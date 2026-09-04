#!/usr/bin/env python3
"""Collect Claude Code and Codex quota windows and serve them to PebbleKit JS."""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

DURATIONS = {300: "5h", 10_080: "7d"}

# Home Assistant entity for the local Koivusyrjä outside temperature (met.no forecast).
HASS_TEMPERATURE_ENTITY = "weather.forecast_koti"
HASS_DEFAULT_SERVER = "http://localhost:8123"


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


# limits[] kinds in the Anthropic usage payload, and the window each maps to. A
# weekly_scoped entry carries a per-model scope (e.g. Fable); its key keeps the
# model name so compact_watch can route it to its own gauge row.
CLAUDE_LIMIT_WINDOWS = {
    "session": ("5h", 18_000),
    "weekly_all": ("7d", 604_800),
}
CLAUDE_SCOPED_DURATION = 604_800


def claude_windows_from_limits(limits: Any) -> dict[str, Any]:
    """The usable windows in a limits[] payload, keyed like the legacy pair.

    Entries with no percent or no resets_at are dropped: a window with no end
    cannot be placed on a burn line. Unknown kinds are skipped.
    """
    windows: dict[str, Any] = {}
    for limit in limits or []:
        if not isinstance(limit, dict):
            continue
        percent = limit.get("percent")
        resets_at = limit.get("resets_at")
        if percent is None or not resets_at:
            continue
        kind = limit.get("kind")
        if kind in CLAUDE_LIMIT_WINDOWS:
            name, seconds = CLAUDE_LIMIT_WINDOWS[kind]
        elif kind == "weekly_scoped":
            scope = (limit.get("scope") or {}).get("model") or {}
            name, seconds = (
                f"7d ({scope.get('display_name') or 'model'})",
                CLAUDE_SCOPED_DURATION,
            )
        else:
            continue
        windows[name] = {
            "used_fraction": fraction(percent),
            "resets_at": resets_at,
            "duration_seconds": seconds,
        }
    return windows


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
    if windows := claude_windows_from_limits(raw.get("limits")):
        return {"service": "claude", "windows": windows}
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


def collect_temperature() -> int | None:
    """Local outside temperature in integer tenths of degC from Home Assistant.

    Returns None (rather than a fabricated value) whenever the reading cannot be
    trusted: no HA token configured, the entity is unknown/unavailable, or the
    temperature attribute is missing. Network/HTTP/JSON failures raise so the
    caller can record the error while still delivering quota data.
    """
    token = os.environ.get("HASS_TOKEN")
    if not token:
        return None
    server = os.environ.get("HASS_SERVER", HASS_DEFAULT_SERVER).rstrip("/")
    request = urllib.request.Request(
        f"{server}/api/states/{HASS_TEMPERATURE_ENTITY}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "pebble-quota/0.1"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        state = json.load(response)
    if state.get("state") in (None, "unknown", "unavailable"):
        return None
    value = state.get("attributes", {}).get("temperature")
    if value is None:
        return None
    return round(float(value) * 10)


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
    # Outside temperature is best-effort: a Home Assistant outage must never block
    # quota delivery, so record the error and omit the value rather than raise.
    try:
        tenths = collect_temperature()
    except Exception as exc:
        output["temperature_error"] = f"{type(exc).__name__}: {exc}"
    else:
        if tenths is not None:
            output["temperature_c_tenths"] = tenths
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
            code, name = service_codes[service_name], window_name
            if service_name == "claude" and window_name == "7d (Fable)":
                code, name = "F", "7d"
            rows.append({
                "s": code,
                "w": name,
                "u": round(used * 100),
                "r": reset,
                "d": duration,
                "p": pace_points(used, reset, duration, now),
            })
    result: dict[str, Any] = {"v": 1, "at": epoch(data.get("collected_at")), "q": rows}
    tenths = data.get("temperature_c_tenths")
    if isinstance(tenths, int):
        result["t"] = tenths  # outside temperature, integer tenths of degC
    return result


def write_snapshot(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)


def has_quota_data(data: dict[str, Any]) -> bool:
    services = data.get("services", {})
    return any(service.get("windows") for service in services.values())


def refresh_snapshot(output: Path) -> dict[str, Any]:
    data = collect_all()
    if not has_quota_data(data):
        if output.exists():
            raise RuntimeError("all quota collectors failed; preserving previous snapshot")
        raise RuntimeError("all quota collectors failed; no snapshot available")
    write_snapshot(data, output)
    return data


def refresh_forever(output: Path, interval_seconds: int, stop: threading.Event) -> None:
    while not stop.wait(interval_seconds):
        try:
            refresh_snapshot(output)
        except Exception as error:
            print(f"quota refresh failed: {error}", file=sys.stderr, flush=True)


class QuotaServer(ThreadingHTTPServer):
    snapshot: Path
    token: str


# Settings page for the Pebble phone app (Clay-style config, no dependency):
# plain form, Save closes the webview with the values as JSON. Served without
# auth so a fresh install can be pointed at the endpoint before it has a token.
CONFIG_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quota Pace settings</title>
<style>body{font-family:sans-serif;margin:1em}label{display:block;margin:0 0 1em}
input{width:100%;box-sizing:border-box;font-size:1em;margin-top:.25em}
button{font-size:1.1em;padding:.5em 1.5em}</style></head>
<body>
<label>Endpoint<input id="endpoint" type="url" autocapitalize="off"></label>
<label>Token<input id="token" type="text" autocapitalize="off" autocomplete="off"></label>
<button id="save">Save</button>
<script>
var q = {};
location.search.slice(1).split("&").forEach(function (pair) {
  var kv = pair.split("=");
  if (kv[0]) q[kv[0]] = decodeURIComponent(kv[1] || "");
});
document.getElementById("endpoint").value = q.endpoint || "";
document.getElementById("token").value = q.token || "";
document.getElementById("save").addEventListener("click", function () {
  var settings = {
    endpoint: document.getElementById("endpoint").value,
    token: document.getElementById("token").value,
  };
  document.location = "pebblejs://close#" + encodeURIComponent(JSON.stringify(settings));
});
</script></body></html>
"""


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/config":
                body = CONFIG_PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path != "/v1/watch":
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

    try:
        refresh_snapshot(args.output)
    except RuntimeError as error:
        if not args.output.exists():
            raise
        print(f"initial quota refresh failed: {error}", file=sys.stderr, flush=True)
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
