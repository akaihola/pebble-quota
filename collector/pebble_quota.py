"""Collect Claude Code and Codex quota windows and serve them to PebbleKit JS."""

from __future__ import annotations

import argparse
import contextlib
import copy
import hmac
import json
import math
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DURATIONS = {300: "5h", 10_080: "7d"}
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CLAUDE_BACKOFF_SECONDS = 600
CLAUDE_MAX_BACKOFF_SECONDS = 3600
CODEX_RPC_TIMEOUT_SECONDS = 15
CODEX_EXIT_TIMEOUT_SECONDS = 2
CODEX_DIAGNOSTICS = {
    f"Codex {stage}: {reason}"
    for stage in ("initialize", "rate limits")
    for reason in ("RPC error (check CLI login and compatibility)", "response timeout",
                   "unexpected EOF", "invalid JSON", "invalid response", "invalid result",
                   "pipe failure")
} | {"Codex rate limits: no quota windows"}


class CodexError(RuntimeError):
    """RPC failure; diagnostic() publishes only allowlisted messages."""


# Home Assistant entity for the local Koivusyrjä outside temperature (met.no forecast).
HASS_TEMPERATURE_ENTITY = "weather.forecast_koti"
HASS_DEFAULT_SERVER = "http://localhost:8123"
HASS_TEMPERATURE_MAX_AGE_SECONDS = 2 * 60 * 60


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


WATCH_INT_MAX = 2**31 - 1
# The watch multiplies duration by 100 in signed 32-bit arithmetic.
MAX_DURATION_SECONDS = WATCH_INT_MAX // 100
DIAGNOSTICS = {"HTTPError", "URLError", "TimeoutError", "RuntimeError", "OSError",
               "ValueError", "JSONDecodeError", "Invalid quota windows", "Quota unavailable"} | CODEX_DIAGNOSTICS


def epoch(value: Any) -> int | None:
    """Return bounded Unix seconds or None; truncate timezone-aware ISO subseconds."""
    try:
        if type(value) in (int, float):
            seconds = value
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            seconds = parsed.timestamp()
        else:
            return None
        if 0 <= seconds <= WATCH_INT_MAX and (isinstance(value, str) or int(seconds) == seconds):
            return int(seconds)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def percent_fraction(value: Any) -> float | None:
    """Provider percentages must be JSON numbers, never numeric strings/bools."""
    if type(value) not in (int, float) or not 0 <= value <= 100:
        return None
    return value / 100.0


def diagnostic(error: Exception) -> str:
    if isinstance(error, CodexError) and str(error) in CODEX_DIAGNOSTICS:
        return str(error)
    name = type(error).__name__
    return name if name in DIAGNOSTICS else "Quota unavailable"


# Watch wire codes. Snapshot labels keep a scope's display name, e.g.
# "7d (Fable)"; the wire carries only the one-letter code and the window.
SERVICE_CODES = {"claude": "C", "codex": "X"}
CLAUDE_SCOPED_CODES = {"Fable": "F"}
# Gauge lines the watch has room for: rows plus one per unavailable provider.
WATCH_LINES = 5


def wire_identity(name: str, label: str) -> tuple[str, str] | None:
    """Bounded (code, window) for a snapshot window label, or None if unsupported."""
    code, window = SERVICE_CODES[name], label
    if name == "claude" and "(" in label:
        window, separator, scope = label.partition(" (")
        code = CLAUDE_SCOPED_CODES.get(scope[:-1]) if separator and scope.endswith(")") else None
        if code is None:
            return None
    if not (1 <= len(window) <= 7 and window.isascii()
            and all(32 <= ord(c) <= 126 for c in window)):
        return None
    return code, window


def normalize_window(name: str, label: Any, item: Any) -> dict[str, Any] | None:
    if not isinstance(label, str) or not isinstance(item, dict) or not wire_identity(name, label):
        return None
    used, duration = item.get("used_fraction"), item.get("duration_seconds")
    reset = epoch(item.get("resets_at"))
    if (type(used) not in (int, float) or not 0 <= used <= 1
            or reset is None or type(duration) is not int
            or not 1 <= duration <= MAX_DURATION_SECONDS):
        return None
    return {"used_fraction": used, "resets_at": reset, "duration_seconds": duration}


def normalize_snapshot(data: Any) -> dict[str, Any]:
    """Untrusted disk/provider input -> usable rows and safe scheduling metadata."""
    if not isinstance(data, dict):
        data = {}
    result: dict[str, Any] = {"services": {}}
    if epoch(data.get("collected_at")) is not None:
        result["collected_at"] = data["collected_at"]
    services = data.get("services")
    if not isinstance(services, dict):
        services = {}
    for name in ("claude", "codex"):
        source = services.get(name)
        if not isinstance(source, dict):
            continue
        service: dict[str, Any] = {}
        result["services"][name] = service
        if source.get("service") == name:
            service["service"] = name
        for field in ("last_attempt_at", "last_success_at", "retry_at"):
            if epoch(source.get(field)) is not None:
                service[field] = source[field]
        failures = source.get("rate_limit_failures")
        if type(failures) is int and 0 < failures <= WATCH_INT_MAX:
            service["rate_limit_failures"] = failures
        if "error" in source:
            error = source["error"]
            service["error"] = error if isinstance(error, str) and error in DIAGNOSTICS else "Quota unavailable"
        if source.get("stale") is True:
            service["stale"] = True
        age = source.get("age_seconds")
        if type(age) is int and 0 <= age <= WATCH_INT_MAX:
            service["age_seconds"] = age
        windows = source.get("windows")
        if not isinstance(windows, dict):
            continue
        valid = {}
        for label, item in windows.items():
            if window := normalize_window(name, label, item):
                valid[label] = window
        if valid:
            service["windows"] = valid
    tenths = data.get("temperature_c_tenths")
    if type(tenths) is int and -WATCH_INT_MAX <= tenths <= WATCH_INT_MAX:
        result["temperature_c_tenths"] = tenths
    if "temperature_error" in data:
        error = data["temperature_error"]
        result["temperature_error"] = error if isinstance(error, str) and error in DIAGNOSTICS else "Quota unavailable"
    return result


def load_snapshot(output: Path) -> dict[str, Any]:
    try:
        return normalize_snapshot(json.loads(output.read_text()))
    except (OSError, ValueError):
        return normalize_snapshot({})


def pace_points(used_fraction: float, resets_at: int, duration_seconds: int, now: int) -> int:
    """Positive means usage is behind time: quota is ahead of sustainable pace."""
    remaining_seconds = max(0, min(duration_seconds, resets_at - now))
    elapsed_fraction = 1.0 - remaining_seconds / duration_seconds
    return round((elapsed_fraction - used_fraction) * 100)


# Unscoped limits[] kinds and their windows. weekly_scoped entries are kept only
# for model scopes in CLAUDE_SCOPED_CODES, labelled "7d (<display name>)".
CLAUDE_LIMIT_WINDOWS = {
    "session": ("5h", 18_000),
    "weekly_all": ("7d", 604_800),
}
CLAUDE_SCOPED_DURATION = 604_800


def claude_windows_from_limits(limits: Any) -> dict[str, Any]:
    """Validated limits[] windows: 5h, 7d and supported scopes such as 7d (Fable).

    Unsupported kinds/scopes and invalid percentages, resets or windows are skipped.
    """
    windows: dict[str, Any] = {}
    for limit in limits if isinstance(limits, list) else []:
        if not isinstance(limit, dict):
            continue
        percent = limit.get("percent")
        resets_at = limit.get("resets_at")
        if percent is None or not resets_at:
            continue
        kind = limit.get("kind")
        if not isinstance(kind, str):
            continue
        if kind in CLAUDE_LIMIT_WINDOWS:
            if limit.get("scope") is not None:
                continue
            name, seconds = CLAUDE_LIMIT_WINDOWS[kind]
        elif kind == "weekly_scoped":
            scope = limit.get("scope")
            if not isinstance(scope, dict) or not isinstance(scope.get("model"), dict):
                continue
            display_name = scope["model"].get("display_name")
            if not isinstance(display_name, str) or display_name not in CLAUDE_SCOPED_CODES:
                continue
            name, seconds = f"7d ({display_name})", CLAUDE_SCOPED_DURATION
        else:
            continue
        window = normalize_window("claude", name, {
            "used_fraction": percent_fraction(percent),
            "resets_at": resets_at,
            "duration_seconds": seconds,
        })
        if window:
            windows[name] = window
    return windows


class NoProviderRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def provider_urlopen(request: urllib.request.Request, timeout: int):
    # Refuse all redirects, including cross-host and HTTPS downgrade redirects.
    return urllib.request.build_opener(NoProviderRedirect()).open(request, timeout=timeout)


def collect_claude() -> dict[str, Any]:
    credentials = json.loads((Path.home() / ".claude/.credentials.json").read_text())
    token = credentials.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        raise RuntimeError("Claude OAuth access token not found")
    request = urllib.request.Request(
        CLAUDE_USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "pebble-quota/0.1",
        },
    )
    with provider_urlopen(request, timeout=15) as response:
        raw = json.load(response)
    if not isinstance(raw, dict):
        return {"service": "claude", "windows": {}}
    if windows := claude_windows_from_limits(raw.get("limits")):
        return {"service": "claude", "windows": windows}
    windows = {}
    for source, name, seconds in (
        ("five_hour", "5h", 18_000),
        ("seven_day", "7d", 604_800),
    ):
        if isinstance(item := raw.get(source), dict):
            windows[name] = {
                "used_fraction": percent_fraction(item.get("utilization")),
                "resets_at": item.get("resets_at"),
                "duration_seconds": seconds,
            }
    return {"service": "claude", "windows": windows}


def codex_service_from_result(result: Any) -> dict[str, Any]:
    """Decode Codex rate limits independently of the app-server lifecycle."""
    if not isinstance(result, dict) or not any(
            key in result for key in ("rateLimits", "primary", "secondary")):
        raise CodexError("Codex rate limits: invalid result")
    limits = result.get("rateLimits", result)
    windows = {}
    if not isinstance(limits, dict):
        raise CodexError("Codex rate limits: invalid result")
    for source in ("primary", "secondary"):
        if not isinstance(item := limits.get(source), dict):
            continue
        minutes = item.get("windowDurationMins")
        if type(minutes) is not int or not 1 <= minutes <= MAX_DURATION_SECONDS // 60:
            continue
        name = DURATIONS.get(minutes, f"{minutes}m")
        window = normalize_window("codex", name, {
            "used_fraction": percent_fraction(item.get("usedPercent")),
            "resets_at": item.get("resetsAt"),
            "duration_seconds": minutes * 60,
        })
        if window:
            windows[name] = window
    if not windows and any(limits.get(key) is not None for key in ("primary", "secondary")):
        raise CodexError("Codex rate limits: invalid result")
    data = {"service": "codex", "windows": windows}
    if not windows:
        data["error"] = "Codex rate limits: no quota windows"
    return data


def collect_codex() -> dict[str, Any]:
    proc = subprocess.Popen(
        ["codex", "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env={"SHELL": "/bin/bash", **{key: value for key, value in os.environ.items()
             if key in {"HOME", "PATH", "TERM", "LANG", "LANGUAGE", "CODEX_HOME",
                        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
                        "LC_ALL", "LC_CTYPE", "LC_NUMERIC", "LC_TIME", "LC_COLLATE",
                        "LC_MONETARY", "LC_MESSAGES", "LC_PAPER", "LC_NAME", "LC_ADDRESS",
                        "LC_TELEPHONE", "LC_MEASUREMENT", "LC_IDENTIFICATION"}}},
    )
    assert proc.stdin is not None and proc.stdout is not None
    stdin, stdout = proc.stdin, proc.stdout
    lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        try:
            for line in stdout:
                lines.put(line)
        except (OSError, UnicodeError):
            lines.put("")  # A read/decode failure, distinct from normal EOF.
        finally:
            lines.put(None)

    reader = threading.Thread(target=read_stdout, daemon=True)

    def send(message: dict[str, Any]) -> None:
        stdin.write(json.dumps(message) + "\n")
        stdin.flush()

    stage = "initialize"
    try:
        reader.start()
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "pebble-quota", "title": "Pebble Quota", "version": "0.1"}
        }})
        deadline = time.monotonic() + CODEX_RPC_TIMEOUT_SECONDS
        request_id = 1
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CodexError(f"Codex {stage}: response timeout")
            try:
                line = lines.get(timeout=remaining)
            except queue.Empty:
                raise CodexError(f"Codex {stage}: response timeout") from None
            if line is None:
                raise CodexError(f"Codex {stage}: unexpected EOF")
            if line == "":
                raise CodexError(f"Codex {stage}: pipe failure")
            try:
                message = json.loads(line)
            except ValueError:
                raise CodexError(f"Codex {stage}: invalid JSON") from None
            if not isinstance(message, dict):
                raise CodexError(f"Codex {stage}: invalid response")
            if "id" not in message and isinstance(message.get("method"), str):
                continue  # Notifications do not advance the handshake or deadline.
            if type(message.get("id")) is not int or message["id"] != request_id:
                raise CodexError(f"Codex {stage}: invalid response")
            if "error" in message:
                raise CodexError(f"Codex {stage}: RPC error (check CLI login and compatibility)")
            result = message.get("result")
            if not isinstance(result, dict):
                raise CodexError(f"Codex {stage}: invalid result")
            if request_id == 1:
                if not isinstance(result.get("userAgent"), str) or not result["userAgent"]:
                    raise CodexError("Codex initialize: invalid result")
                stage = "rate limits"
                send({"method": "initialized", "params": {}})
                send({"id": 2, "method": "account/rateLimits/read", "params": {}})
                request_id = 2
            else:
                return codex_service_from_result(result)
    except OSError:
        raise CodexError(f"Codex {stage}: pipe failure") from None
    finally:
        try:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=CODEX_EXIT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        finally:
            if reader.ident is not None:
                reader.join()
            for pipe in (stdin, stdout):
                with contextlib.suppress(OSError):
                    pipe.close()


def collect_temperature() -> int | None:
    """Local outside temperature in integer tenths of degC from Home Assistant.

    Returns None (rather than a fabricated value) whenever the reading cannot be
    trusted: missing token, unavailable entity, invalid value/unit, or missing,
    future or older-than-two-hours last_updated. Network/HTTP/JSON failures raise
    so the caller can record the error while still delivering quota data.
    """
    token = os.environ.get("HASS_TOKEN")
    if not token:
        return None
    server = os.environ.get("HASS_SERVER", HASS_DEFAULT_SERVER).rstrip("/")
    request = urllib.request.Request(
        f"{server}/api/states/{HASS_TEMPERATURE_ENTITY}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "pebble-quota/0.1"},
    )
    with provider_urlopen(request, timeout=5) as response:
        state = json.load(response)
    if not isinstance(state, dict) or state.get("state") in (None, "unknown", "unavailable"):
        return None
    attributes = state.get("attributes")
    if not isinstance(attributes, dict):
        return None
    value = attributes.get("temperature")
    unit = attributes.get("temperature_unit")
    if (type(value) not in (int, float) or not math.isfinite(value)
            or unit not in ("°C", "°F")):
        return None
    updated = state.get("last_updated")
    if not isinstance(updated, str):
        return None
    try:
        updated_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError:
        return None
    if updated_at.tzinfo is None:
        return None
    # HA entity age is a proxy; it does not certify the weather observation time.
    age = time.time() - updated_at.timestamp()
    if not 0 <= age <= HASS_TEMPERATURE_MAX_AGE_SECONDS:
        return None
    celsius = (value - 32) * 5 / 9 if unit == "°F" else value
    return round(celsius * 10)


def claude_retry_delay(retry_after: str | None, failures: int, now: int) -> float:
    """Honor useful Retry-After values; zero/malformed values need real backoff."""
    if retry_after:
        retry_after = retry_after.strip()
        try:
            delay = (int(retry_after) if retry_after.isdigit()
                     else parsedate_to_datetime(retry_after).timestamp() - now)
            if delay > 0:
                # Reject out-of-range dates before persisting a retry deadline.
                iso_from_epoch(now + delay)
                return delay
        except (ValueError, TypeError, OverflowError, OSError):
            pass
    return min(CLAUDE_MAX_BACKOFF_SECONDS,
               CLAUDE_BACKOFF_SECONDS * 2 ** min(failures - 1, 3))


def collect_all(previous: dict[str, Any] | None = None, interval_seconds: int = 0,
                before_attempt: Callable[[str, str], None] | None = None) -> dict[str, Any]:
    output: dict[str, Any] = {"collected_at": utc_iso(), "services": {}}
    now = epoch(output["collected_at"])
    assert now is not None
    previous = normalize_snapshot(previous)
    old_claude = previous.get("services", {}).get("claude", {})
    collectors: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
        ("claude", collect_claude), ("codex", collect_codex)
    )
    for name, collector in collectors:
        old_service = previous.get("services", {}).get(name, {})
        last_attempt = epoch(old_service.get("last_attempt_at"))
        if last_attempt is not None and now < last_attempt + interval_seconds:
            output["services"][name] = dict(old_service)
            continue
        if name == "claude" and (epoch(old_claude.get("retry_at")) or 0) > now:
            output["services"][name] = dict(old_claude)
            continue
        if before_attempt is not None:
            before_attempt(name, output["collected_at"])
        try:
            output["services"][name] = normalize_snapshot(
                {"services": {name: collector()}})["services"].get(name, {})
            if not output["services"][name].get("windows"):
                output["services"][name].setdefault("error", "Invalid quota windows")
            if output["services"][name].get("windows"):
                output["services"][name]["last_success_at"] = output["collected_at"]
        except Exception as exc:  # noqa: BLE001 - isolate providers; record, then collect the next
            service = {"service": name, "error": diagnostic(exc)}
            output["services"][name] = service
            if name == "claude" and isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                failures = old_claude.get("rate_limit_failures", 0) + 1
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                retry_now = epoch(utc_iso()) or now
                service["rate_limit_failures"] = failures
                service["retry_at"] = iso_from_epoch(
                    retry_now + claude_retry_delay(retry_after, failures, retry_now))
            if isinstance(exc, urllib.error.HTTPError):
                exc.close()
        output["services"][name]["last_attempt_at"] = output["collected_at"]
    claude = output["services"]["claude"]
    if "error" in claude and old_claude.get("windows"):
        last_success = old_claude.get("last_success_at", previous.get("collected_at"))
        claude.update(
            windows=old_claude["windows"], last_success_at=last_success,
            stale=True, age_seconds=max(0, now - (epoch(last_success) or 0)),
        )
    # Outside temperature is best-effort: a Home Assistant outage must never block
    # quota delivery, so record the error and omit the value rather than raise.
    try:
        tenths = collect_temperature()
    except Exception as exc:  # noqa: BLE001 - best-effort, see above
        output["temperature_error"] = diagnostic(exc)
    else:
        if tenths is not None:
            output["temperature_c_tenths"] = tenths
    return output


def compact_watch(data: dict[str, Any], now: int | None = None) -> dict[str, Any]:
    data = normalize_snapshot(data)
    now = int(time.time()) if now is None else now
    at = epoch(data.get("collected_at"))
    ranked = []
    unavailable = ""
    for provider, (service_name, service_code) in enumerate(SERVICE_CODES.items()):
        service = data.get("services", {}).get(service_name, {})
        if not service.get("windows"):
            unavailable += service_code
        # Retained rows keep their own reading time; the pass time is only a fallback.
        observed = epoch(service.get("last_success_at"))
        observed = at if observed is None else observed
        failed = service.get("stale") is True or "error" in service
        for label, item in service.get("windows", {}).items():
            used = item["used_fraction"]
            reset = item["resets_at"]
            duration = item["duration_seconds"]
            identity = wire_identity(service_name, label)
            assert identity is not None  # normalize_snapshot keeps only valid labels
            code, name = identity
            row = {
                "s": code,
                "w": name,
                "u": round(used * 100),
                "r": reset,
                "d": duration,
                "p": pace_points(used, reset, duration, now),
            }
            if observed is not None:
                row["o"] = observed
            if failed:
                row["e"] = 1
            # Priority: core (unscoped) before scoped, provider, shorter window, code, label.
            ranked.append(((code != service_code, provider, duration, code, name), row))
    # Each provider in n takes one of the watch's lines; rows fill the rest by
    # priority and go out in display order, each provider's rows together.
    chosen = sorted(ranked, key=lambda item: item[0])[:WATCH_LINES - len(unavailable)]
    chosen.sort(key=lambda item: (item[0][1], item[0][0], *item[0][2:]))
    result: dict[str, Any] = {"v": 1, "at": at, "q": [row for _, row in chosen]}
    if unavailable:
        result["n"] = unavailable  # providers without rows, e.g. after a failed Codex read
    if "temperature_c_tenths" in data:
        result["t"] = data["temperature_c_tenths"]  # outside temperature, integer tenths of degC
    return result


def write_snapshot(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=output.parent, prefix=output.name + ".", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def has_quota_data(data: Any) -> bool:
    return any(service.get("windows")
               for service in normalize_snapshot(data)["services"].values())


def merge_unavailable_snapshot(previous: dict[str, Any], attempted: dict[str, Any]) -> dict[str, Any]:
    """Previous quota, collection time and temperature plus attempted service metadata.

    Both are normalized snapshots and attempted has no quota rows; neither is
    modified. Attempt, cooldown and error fields replace old ones. A scheduling-only
    snapshot is never a successful quota read, so retained rows become stale and
    age from their last success until the attempted collection time.
    """
    merged = copy.deepcopy(previous)
    for name, service in attempted["services"].items():
        old = merged["services"].setdefault(name, {})
        old.update(service)
        if old.get("windows"):
            old["stale"] = True
            last_success = old.get("last_success_at", previous.get("collected_at"))
            success_epoch = epoch(last_success)
            if success_epoch is not None:
                old["last_success_at"] = last_success
                old["age_seconds"] = max(0, (epoch(attempted.get("collected_at")) or 0)
                                         - success_epoch)
    return merged


def refresh_snapshot(output: Path, previous: dict[str, Any] | None = None,
                     interval_seconds: int = 0) -> dict[str, Any]:
    state = load_snapshot(output) if previous is None else normalize_snapshot(previous)

    def before_attempt(name: str, attempted_at: str) -> None:
        state["services"].setdefault(name, {})["last_attempt_at"] = attempted_at
        # Persist attempt time so restarts respect the configured refresh interval.
        try:
            write_snapshot(state, output)
        except OSError as error:
            print(f"attempt persistence failed: {diagnostic(error)}", file=sys.stderr, flush=True)

    if interval_seconds:
        data = normalize_snapshot(collect_all(state, interval_seconds, before_attempt))
    else:
        data = normalize_snapshot(collect_all(state))
    available = has_quota_data(data)
    retained = has_quota_data(state)
    if not available:
        data = merge_unavailable_snapshot(state, data)
    if previous is not None:
        previous.clear()
        previous.update(data)  # Keep cooldown in memory even when disk writes fail.
    write_snapshot(data, output)
    if not available:
        message = "preserving previous snapshot" if retained else "no snapshot available"
        raise RuntimeError(f"all quota collectors failed; {message}")
    return data


def refresh_forever(output: Path, interval_seconds: int, stop: threading.Event) -> None:
    previous = load_snapshot(output)
    while not stop.is_set():
        try:
            refresh_snapshot(output, previous, interval_seconds)
        except Exception as error:  # noqa: BLE001 - keep refreshing and serving after any failure
            print(f"quota refresh failed: {diagnostic(error)}", file=sys.stderr, flush=True)
        if stop.wait(interval_seconds):
            break


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


class Handler(BaseHTTPRequestHandler):
    server: QuotaServer

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
        expected = f"Bearer {self.server.token}"
        if not self.server.token or not hmac.compare_digest(self.headers.get("Authorization", "").encode(), expected.encode()):
            self.send_error(401)
            return
        try:
            data = json.loads(self.server.snapshot.read_text())
            payload = compact_watch(data)
            if not payload["q"] or payload["at"] is None:
                raise ValueError("Snapshot unavailable")
            body = json.dumps(payload, separators=(",", ":")).encode()
        except Exception as exc:  # noqa: BLE001 - any unreadable snapshot is a 503, not a dropped connection
            print(f"snapshot response failed: {diagnostic(exc)}",
                  file=sys.stderr, flush=True)
            self.send_error(503, "Snapshot unavailable")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


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

    server = QuotaServer((args.host, args.port), Handler)
    server.snapshot, server.token = args.output, token
    stop = threading.Event()
    refresher = threading.Thread(
        target=refresh_forever,
        args=(args.output, args.refresh_seconds, stop),
        daemon=True,
    )
    refresher.start()
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
