#!/usr/bin/env python3
"""PROTOTYPE: read Claude Code and Codex quota windows without exposing credentials."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def iso_from_epoch(value: int | float | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.isdigit():
        return value
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat().replace("+00:00", "Z")


def fraction(value: int | float | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result / 100.0 if result > 1 else result


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
            "User-Agent": "pebble-quota-prototype/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = json.load(response)

    windows = {}
    for source, name, seconds in (
        ("five_hour", "5h", 5 * 60 * 60),
        ("seven_day", "7d", 7 * 24 * 60 * 60),
    ):
        item = raw.get(source)
        if item:
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
    stdin = proc.stdin
    stdout = proc.stdout
    lines: queue.Queue[str] = queue.Queue()

    def read_stdout() -> None:
        for line in stdout:
            lines.put(line)

    threading.Thread(target=read_stdout, daemon=True).start()

    def send(message: dict[str, Any]) -> None:
        stdin.write(json.dumps(message) + "\n")
        stdin.flush()

    try:
        send({
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "pebble-quota", "title": "Pebble Quota", "version": "0.1"}},
        })
        deadline = time.monotonic() + 15
        initialized = False
        while time.monotonic() < deadline:
            message = json.loads(lines.get(timeout=max(0.1, deadline - time.monotonic())))
            if message.get("id") == 1:
                send({"method": "initialized", "params": {}})
                send({"id": 2, "method": "account/rateLimits/read", "params": {}})
                initialized = True
            elif message.get("id") == 2:
                result = message.get("result", {})
                rate_limits = result.get("rateLimits", result)
                windows = {}
                for source in ("primary", "secondary"):
                    item = rate_limits.get(source)
                    if not item:
                        continue
                    duration_minutes = item.get("windowDurationMins")
                    duration_seconds = int(duration_minutes * 60) if duration_minutes else None
                    if duration_minutes == 5 * 60:
                        name = "5h"
                    elif duration_minutes == 7 * 24 * 60:
                        name = "7d"
                    elif duration_minutes:
                        name = f"{duration_minutes}m"
                    else:
                        name = source
                    windows[name] = {
                        "used_fraction": fraction(item.get("usedPercent")),
                        "resets_at": iso_from_epoch(item.get("resetsAt")),
                        "duration_seconds": duration_seconds,
                    }
                return {"service": "codex", "windows": windows}
        raise TimeoutError(f"Codex app-server did not return rate limits (initialized={initialized})")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    output: dict[str, Any] = {
        "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "services": {},
    }
    for name, collector in (("claude", collect_claude), ("codex", collect_codex)):
        try:
            output["services"][name] = collector()
        except Exception as exc:
            output["services"][name] = {"service": name, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
