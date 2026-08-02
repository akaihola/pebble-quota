#!/usr/bin/env python3
"""Collect Claude Code and Codex quota windows and serve them to PebbleKit JS."""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

DURATIONS = {300: "5h", 10_080: "7d"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iso_from_epoch(value: int | float | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.isdigit():
        return value
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat().replace("+00:00", "Z")


def epoch(value: int | float | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) or value.isdigit():
        return int(float(value))
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def fraction(value: int | float | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result / 100.0 if result > 1 else result


def pace_points(used_fraction: float, resets_at: int, duration_seconds: int, now: int) -> int:
    """Positive means usage is behind time: quota is ahead of sustainable pace."""
    remaining_seconds = max(0, min(duration_seconds, resets_at - now))
    elapsed_fraction = 1.0 - remaining_seconds / duration_seconds
    return round((elapsed_fraction - used_fraction) * 100)


def collect_claude() -> dict[str, Any]:
    credentials = json.loads((Path.home() / ".claude/.credentials.json").read_text())
    token = credentials.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        raise RuntimeError("Claude OAuth access token not found")
    request = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "pebble-quota/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = json.load(response)
    windows = {}
    for source, name, seconds in (
        ("five_hour", "5h", 18_000),
        ("seven_day", "7d", 604_800),
    ):
        if item := raw.get(source):
            windows[name] = {
                "used_fraction": fraction(item.get("utilization")),
                "resets_at": item.get("resets_at"),
                "duration_seconds": seconds,
            }
    return {"service": "claude", "windows": windows}


def collect_codex() -> dict[str, Any]:
    proc = subprocess.Popen(
        ["codex", "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    assert proc.stdin is not None and proc.stdout is not None
    stdin, stdout = proc.stdin, proc.stdout
    lines: queue.Queue[str] = queue.Queue()

    def read_stdout() -> None:
        for line in stdout:
            lines.put(line)

    threading.Thread(target=read_stdout, daemon=True).start()

    def send(message: dict[str, Any]) -> None:
        stdin.write(json.dumps(message) + "\n")
        stdin.flush()

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "pebble-quota", "title": "Pebble Quota", "version": "0.1"}
        }})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            message = json.loads(lines.get(timeout=max(0.1, deadline - time.monotonic())))
            if message.get("id") == 1:
                send({"method": "initialized", "params": {}})
                send({"id": 2, "method": "account/rateLimits/read", "params": {}})
            elif message.get("id") == 2:
                result = message.get("result", {})
                limits = result.get("rateLimits", result)
                windows = {}
                for source in ("primary", "secondary"):
                    if not (item := limits.get(source)):
                        continue
                    minutes = item.get("windowDurationMins")
                    name = DURATIONS.get(minutes, f"{minutes}m" if minutes else source)
                    windows[name] = {
                        "used_fraction": fraction(item.get("usedPercent")),
                        "resets_at": iso_from_epoch(item.get("resetsAt")),
                        "duration_seconds": int(minutes * 60) if minutes else None,
                    }
                return {"service": "codex", "windows": windows}
        raise TimeoutError("Codex app-server did not return rate limits")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def collect_all() -> dict[str, Any]:
    output: dict[str, Any] = {"collected_at": utc_iso(), "services": {}}
    collectors: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
        ("claude", collect_claude), ("codex", collect_codex)
    )
    for name, collector in collectors:
        try:
            output["services"][name] = collector()
        except Exception as exc:
            output["services"][name] = {"service": name, "error": f"{type(exc).__name__}: {exc}"}
    return output


def compact_watch(data: dict[str, Any], now: int | None = None) -> dict[str, Any]:
    now = int(time.time()) if now is None else now
    rows = []
    service_codes = {"claude": "C", "codex": "X"}
    for service_name in ("claude", "codex"):
        service = data.get("services", {}).get(service_name, {})
        for window_name, item in service.get("windows", {}).items():
            used = item.get("used_fraction")
            reset = epoch(item.get("resets_at"))
            duration = item.get("duration_seconds")
            if used is None or reset is None or not duration:
                continue
            rows.append({
                "s": service_codes[service_name],
                "w": window_name,
                "u": round(used * 100),
                "r": reset,
                "d": duration,
                "p": pace_points(used, reset, duration, now),
            })
    return {"v": 1, "at": epoch(data.get("collected_at")), "q": rows}


def write_snapshot(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)


def refresh_snapshot(output: Path) -> dict[str, Any]:
    data = collect_all()
    write_snapshot(data, output)
    return data


def refresh_forever(output: Path, interval_seconds: int, stop: threading.Event) -> None:
    while not stop.wait(interval_seconds):
        refresh_snapshot(output)


class QuotaServer(ThreadingHTTPServer):
    snapshot: Path
    token: str


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/v1/watch":
                self.send_error(404)
                return
            expected = f"Bearer {self.server.token}"  # type: ignore[attr-defined]
            if not self.server.token or self.headers.get("Authorization") != expected:  # type: ignore[attr-defined]
                self.send_error(401)
                return
            try:
                data = json.loads(self.server.snapshot.read_text())  # type: ignore[attr-defined]
                body = json.dumps(compact_watch(data), separators=(",", ":")).encode()
            except Exception as exc:
                self.send_error(503, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("collect", "serve"))
    parser.add_argument("--output", type=Path, default=Path("latest.json"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--refresh-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.command == "collect":
        data = refresh_snapshot(args.output)
        print(json.dumps(compact_watch(data), separators=(",", ":")))
        return
    token = os.environ.get("PEBBLE_QUOTA_TOKEN", "")
    if not token:
        raise SystemExit("PEBBLE_QUOTA_TOKEN is required")
    if args.refresh_seconds < 1:
        raise SystemExit("--refresh-seconds must be positive")

    refresh_snapshot(args.output)
    stop = threading.Event()
    refresher = threading.Thread(
        target=refresh_forever,
        args=(args.output, args.refresh_seconds, stop),
        daemon=True,
    )
    refresher.start()
    server = QuotaServer((args.host, args.port), make_handler())
    server.snapshot, server.token = args.output, token
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
