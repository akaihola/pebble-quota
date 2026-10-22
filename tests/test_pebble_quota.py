from __future__ import annotations

import builtins
import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Any, ClassVar, Self
from unittest import mock

MODULE_PATH = Path(__file__).parents[1] / "collector/pebble_quota.py"
spec = importlib.util.spec_from_file_location("pebble_quota", MODULE_PATH)
assert spec and spec.loader
quota = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quota)


class LiveAccessError(BaseException):
    """Must escape the collector's broad Exception handlers."""


_TOOL_PATH = os.environ["PATH"]
_REAL_POPEN = subprocess.Popen


def setUpModule():
    stack = contextlib.ExitStack()
    unittest.addModuleCleanup(stack.close)
    directories = []
    real_mkdtemp = tempfile.mkdtemp

    def mkdtemp(*args, **kwargs):
        name = real_mkdtemp(*args, **kwargs)
        directories.append(Path(name).resolve())
        return name

    stack.enter_context(mock.patch.object(tempfile, "mkdtemp", mkdtemp))
    home = stack.enter_context(tempfile.TemporaryDirectory())
    stack.enter_context(mock.patch.dict(os.environ, {"HOME": home, "PATH": os.defpath}, clear=True))

    def guarded_open(original):
        def open_file(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(file))
                if not path.is_absolute() and kwargs.get("dir_fd") is not None:
                    path = Path(os.readlink(f"/proc/self/fd/{kwargs['dir_fd']}")) / path
                path = path.resolve()
                if ({".claude", ".codex"} & set(path.parts)
                        and not any(path.is_relative_to(root) for root in directories)):
                    raise LiveAccessError("test attempted real credential access")
            return original(file, *args, **kwargs)
        return open_file

    stack.enter_context(mock.patch.object(builtins, "open", guarded_open(builtins.open)))
    stack.enter_context(mock.patch.object(io, "open", guarded_open(io.open)))
    stack.enter_context(mock.patch.object(os, "open", guarded_open(os.open)))
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def local_only(host):
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise LiveAccessError("test attempted non-loopback network access")

    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            local_only(address[0])
        return real_connect(sock, address)

    def getaddrinfo(host, *args, **kwargs):
        local_only(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def no_process(*args, **kwargs):
        raise LiveAccessError("test must explicitly substitute a fake subprocess")

    stack.enter_context(mock.patch.object(socket.socket, "connect", connect))
    stack.enter_context(mock.patch.object(socket, "getaddrinfo", getaddrinfo))
    stack.enter_context(mock.patch.object(subprocess, "Popen", no_process))


class PaceTests(unittest.TestCase):
    def test_exactly_on_pace(self) -> None:
        self.assertEqual(quota.pace_points(0.5, 1000, 100, 950), 0)

    def test_ahead_has_positive_points(self) -> None:
        self.assertEqual(quota.pace_points(0.2, 1000, 100, 950), 30)

    def test_behind_has_negative_points(self) -> None:
        self.assertEqual(quota.pace_points(0.8, 1000, 100, 950), -30)

    def test_clamps_time_outside_window(self) -> None:
        self.assertEqual(quota.pace_points(0.0, 1200, 100, 1000), 0)
        self.assertEqual(quota.pace_points(1.0, 900, 100, 1000), 0)


class PercentFractionTests(unittest.TestCase):
    def test_codex_used_percent_is_always_a_percentage(self) -> None:
        self.assertEqual(quota.percent_fraction(0), 0.0)
        self.assertEqual(quota.percent_fraction(1), 0.01)
        self.assertEqual(quota.percent_fraction(100), 1.0)

    def test_missing_used_percent_is_none(self) -> None:
        self.assertIsNone(quota.percent_fraction(None))


class CompactTests(unittest.TestCase):
    def test_compacts_and_sorts_services(self) -> None:
        data = {
            "collected_at": "1970-01-01T00:15:00Z",
            "services": {
                "claude": {"windows": {"5h": {
                    "used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100,
                }}},
                "codex": {"windows": {"7d": {
                    "used_fraction": 0.8, "resets_at": 1000, "duration_seconds": 100,
                }}},
            },
        }
        result = quota.compact_watch(data, now=950)
        self.assertEqual(result["v"], 1)
        self.assertEqual(result["at"], 900)
        self.assertEqual(result["q"], [
            {"s": "C", "w": "5h", "u": 20, "r": 1000, "d": 100, "p": 30},
            {"s": "X", "w": "7d", "u": 80, "r": 1000, "d": 100, "p": -30},
        ])

    def test_skips_incomplete_windows(self) -> None:
        data = {"collected_at": 0, "services": {"claude": {"windows": {
            "5h": {"used_fraction": None, "resets_at": None, "duration_seconds": 18_000}
        }}}}
        self.assertEqual(quota.compact_watch(data, now=0)["q"], [])

    def test_routes_fable_window_to_its_own_row(self) -> None:
        data = {"collected_at": 0, "services": {"claude": {"windows": {
            "5h": {"used_fraction": 0.05, "resets_at": 1000, "duration_seconds": 100},
            "7d": {"used_fraction": 0.4, "resets_at": 1000, "duration_seconds": 100},
            "7d (Fable)": {
                "used_fraction": 0.55, "resets_at": 1000, "duration_seconds": 100,
            },
        }}}}
        rows = quota.compact_watch(data, now=950)["q"]
        self.assertEqual([(row["s"], row["w"]) for row in rows],
                         [("C", "5h"), ("C", "7d"), ("F", "7d")])
        self.assertEqual([row["u"] for row in rows], [5, 40, 55])


class RefreshTests(unittest.TestCase):
    def test_refresh_collects_and_atomically_writes_snapshot(self) -> None:
        expected = {
            "collected_at": "1970-01-01T00:00:00Z",
            "services": {"claude": {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "state/latest.json"
            with mock.patch.object(quota, "collect_all", return_value=expected):
                result = quota.refresh_snapshot(output)
            self.assertEqual(result, expected)
            self.assertEqual(json.loads(output.read_text()), expected)
            self.assertFalse(output.with_suffix(".json.tmp").exists())

    def test_total_failure_preserves_previous_snapshot(self) -> None:
        previous = {
            "collected_at": "1970-01-01T00:00:00Z",
            "services": {"claude": {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}},
        }
        failed = {
            "collected_at": "1970-01-01T00:05:00Z",
            "services": {
                "claude": {"error": "offline"},
                "codex": {"error": "offline"},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            output.write_text(json.dumps(previous))
            with mock.patch.object(quota, "collect_all", return_value=failed), \
                 self.assertRaisesRegex(RuntimeError, "preserving previous"):
                quota.refresh_snapshot(output)
            saved = json.loads(output.read_text())
            self.assertEqual(saved["collected_at"], previous["collected_at"])
            self.assertEqual(saved["services"]["claude"]["windows"], previous["services"]["claude"]["windows"])


class UnavailableMergeTests(unittest.TestCase):
    WINDOWS: ClassVar[dict[str, Any]] = {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}

    def test_keeps_old_quota_time_and_temperature_with_new_attempts(self):
        previous = {"collected_at": quota.iso_from_epoch(100), "services": {
            "claude": {"windows": self.WINDOWS, "last_success_at": quota.iso_from_epoch(40),
                       "last_attempt_at": quota.iso_from_epoch(100), "error": "Invalid quota windows"},
            "codex": {"windows": self.WINDOWS},
        }, "temperature_c_tenths": 222}
        claude = {"service": "claude", "error": "HTTPError", "rate_limit_failures": 2,
                  "retry_at": quota.iso_from_epoch(1600), "last_attempt_at": quota.iso_from_epoch(400)}
        codex = {"service": "codex", "error": "RuntimeError", "last_attempt_at": quota.iso_from_epoch(400)}
        attempted = {"collected_at": quota.iso_from_epoch(400), "services": {"claude": claude, "codex": codex},
                     "temperature_error": "URLError"}
        inputs = copy.deepcopy((previous, attempted))
        merged = quota.merge_unavailable_snapshot(previous, attempted)
        self.assertEqual((previous, attempted), inputs)
        self.assertEqual(merged, {"collected_at": quota.iso_from_epoch(100), "services": {
            "claude": dict(claude, windows=self.WINDOWS, last_success_at=quota.iso_from_epoch(40),
                           stale=True, age_seconds=360),
            "codex": dict(codex, windows=self.WINDOWS, last_success_at=quota.iso_from_epoch(100),
                          stale=True, age_seconds=300),
        }, "temperature_c_tenths": 222})

    def test_stale_age_counts_from_last_success_or_old_collection(self):
        attempted = {"collected_at": quota.iso_from_epoch(400), "services": {"codex": {"error": "RuntimeError"}}}
        for collected_at, last_success, expected in (
                (100, None, {"last_success_at": quota.iso_from_epoch(100), "age_seconds": 300}),
                (100, 40, {"last_success_at": quota.iso_from_epoch(40), "age_seconds": 360}),
                (100, 500, {"last_success_at": quota.iso_from_epoch(500), "age_seconds": 0}),
                (None, None, {})):
            with self.subTest(collected_at=collected_at, last_success=last_success):
                service: dict[str, Any] = {"windows": self.WINDOWS}
                if last_success is not None:
                    service["last_success_at"] = quota.iso_from_epoch(last_success)
                previous: dict[str, Any] = {"services": {"codex": service}}
                if collected_at is not None:
                    previous["collected_at"] = quota.iso_from_epoch(collected_at)
                merged = quota.merge_unavailable_snapshot(previous, attempted)
                self.assertEqual(merged["services"]["codex"], dict(
                    windows=self.WINDOWS, error="RuntimeError", stale=True, **expected))

    def test_empty_previous_state_stays_unavailable(self):
        attempted = {"collected_at": quota.iso_from_epoch(300), "services": {
            "claude": {"service": "claude", "error": "HTTPError", "rate_limit_failures": 1,
                       "retry_at": quota.iso_from_epoch(900), "last_attempt_at": quota.iso_from_epoch(300)},
            "codex": {"service": "codex", "error": "RuntimeError"},
        }, "temperature_c_tenths": 111}
        merged = quota.merge_unavailable_snapshot({"services": {}}, attempted)
        self.assertEqual(merged, {"services": attempted["services"]})
        self.assertFalse(quota.has_quota_data(merged))
        self.assertEqual(quota.compact_watch(merged, now=300), {"v": 1, "at": None, "q": []})


class ClaudeBackoffTests(unittest.TestCase):
    PAYLOAD: ClassVar[dict[str, Any]] = {"five_hour": {"utilization": 20, "resets_at": 18000}}

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        home = Path(directory)
        credentials = home / ".claude/.credentials.json"
        credentials.parent.mkdir()
        credentials.write_text(json.dumps({"claudeAiOauth": {"accessToken": "test"}}))
        self.enterContext(mock.patch.object(quota.Path, "home", return_value=home))
        self.output = home / "latest.json"
        self.now = 0
        self.enterContext(mock.patch.object(
            quota, "utc_iso", side_effect=lambda: quota.iso_from_epoch(self.now)))
        self.codex = self.enterContext(mock.patch.object(
            quota, "collect_codex", return_value={"service": "codex", "windows": {}}))
        self.enterContext(mock.patch.object(quota, "collect_temperature", return_value=222))
        self.http = self.enterContext(mock.patch.object(
            quota, "provider_urlopen",
            side_effect=lambda *args, **kwargs: _FakeResponse(self.PAYLOAD)))

    def http_error(self, retry_after: str | None = None, code: int = 429) -> None:
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        self.http.side_effect = urllib.error.HTTPError(
            "https://api.anthropic.com/api/oauth/usage", code, "Too Many Requests",
            headers, None)

    def refresh(self) -> dict:
        try:
            data = quota.refresh_snapshot(self.output)
        except RuntimeError:
            data = json.loads(self.output.read_text())
            self.assertFalse(quota.has_quota_data(data))
        return data["services"]["claude"]

    def test_429_keeps_windows_and_persists_cooldown_until_recovery(self) -> None:
        good = self.refresh()
        self.now = 300
        self.http_error("1200")
        stale = self.refresh()
        self.assertEqual(stale["windows"], good["windows"])
        self.assertTrue(stale["stale"])
        self.assertEqual(stale["last_success_at"], quota.iso_from_epoch(0))
        self.assertEqual(stale["age_seconds"], 300)
        self.assertIn("HTTPError", stale["error"])
        self.assertEqual(quota.epoch(stale["retry_at"]), 1500)
        self.assertEqual(stale["rate_limit_failures"], 1)
        # Each refresh reloads state from disk, including a restarted collector.
        self.now = 1499
        self.http.reset_mock()
        cooling = self.refresh()
        self.http.assert_not_called()
        self.assertEqual(cooling["age_seconds"], 1499)
        self.assertEqual(cooling["retry_at"], stale["retry_at"])
        self.assertEqual(cooling["error"], stale["error"])
        self.assertEqual(self.codex.call_count, 3)
        snapshot = json.loads(self.output.read_text())
        self.assertEqual(snapshot["temperature_c_tenths"], 222)
        self.assertEqual(quota.compact_watch(snapshot, now=self.now)["q"][0]["u"], 20)
        # The steward's existing errors and windows comprehensions still work.
        self.assertEqual({name: data["error"] for name, data in snapshot["services"].items()
                          if "error" in data}, {"claude": stale["error"], "codex": "Invalid quota windows"})
        self.assertEqual([label for data in snapshot["services"].values()
                          for label in data.get("windows", {})], ["5h"])
        self.now = 1500
        self.http.side_effect = lambda *args, **kwargs: _FakeResponse(self.PAYLOAD)
        recovered = self.refresh()
        self.http.assert_called_once()
        self.assertEqual(recovered["last_success_at"], quota.iso_from_epoch(1500))
        for key in ("error", "stale", "age_seconds", "retry_at", "rate_limit_failures"):
            self.assertNotIn(key, recovered)
        self.now = 1800
        self.http_error()
        self.assertEqual(self.refresh()["rate_limit_failures"], 1)

    def test_retry_delay_starts_when_the_429_response_arrives(self) -> None:
        self.now = 300
        self.http_error("60")
        error = self.http.side_effect

        def delayed_error(*args: object, **kwargs: object) -> None:
            self.now += 15
            raise error

        self.http.side_effect = delayed_error
        self.assertEqual(quota.epoch(self.refresh()["retry_at"]), 375)

    def test_both_providers_failing_still_records_claude_staleness(self) -> None:
        self.refresh()
        self.now = 300
        self.http_error()
        self.codex.side_effect = RuntimeError("offline")
        result = self.refresh()
        self.assertTrue(result["stale"])
        self.assertEqual(result["age_seconds"], 300)
        self.assertEqual("RuntimeError", json.loads(self.output.read_text())["services"]["codex"]["error"])

    def test_http_date_retry_after(self) -> None:
        self.http_error("Thu, 01 Jan 1970 02:00:00 GMT")
        result = self.refresh()
        self.assertEqual(quota.epoch(result["retry_at"]), 7200)
        self.assertIn("error", result)
        self.assertNotIn("windows", result)
        self.assertNotIn("stale", result)
        self.now = 7199
        self.http.reset_mock()
        self.refresh()
        self.http.assert_not_called()

    def test_unhelpful_retry_after_uses_exponential_backoff_with_cap(self) -> None:
        for header in (None, "0", "invalid", "-1", "9" * 100,
                       "Wed, 31 Dec 1969 23:59:59 GMT"):
            with self.subTest(header=header):
                self.output.unlink(missing_ok=True)
                self.now = 0
                for failures, delay in enumerate((600, 1200, 2400, 3600, 3600), 1):
                    self.http_error(header)
                    result = self.refresh()
                    self.assertEqual(result["rate_limit_failures"], failures)
                    self.assertEqual(quota.epoch(result["retry_at"]), self.now + delay)
                    self.now += delay - 1
                    self.http.reset_mock()
                    self.refresh()
                    self.http.assert_not_called()
                    self.now += 1

    def test_old_snapshot_gets_original_reading_age_on_other_errors(self) -> None:
        previous = {"collected_at": quota.iso_from_epoch(0), "services": {
            "claude": {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}}}
        self.output.write_text(json.dumps(previous))
        self.now = 300
        self.http_error(code=503)
        result = self.refresh()
        self.assertTrue(result["stale"])
        self.assertEqual(result["age_seconds"], 300)
        self.assertNotIn("retry_at", result)
        self.now = 600
        self.http.reset_mock()
        result = self.refresh()
        self.http.assert_called_once()
        self.assertEqual(result["age_seconds"], 600)

    def test_codex_continues_refreshing_while_claude_has_no_reading(self) -> None:
        self.codex.return_value = {"windows": {"5h": {"used_fraction": 0.1, "resets_at": 1000, "duration_seconds": 100}}}
        self.http_error("900")
        first = self.refresh()
        self.assertNotIn("windows", first)
        self.now = 300
        self.codex.return_value = {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}
        self.http.reset_mock()
        self.refresh()
        self.http.assert_not_called()
        self.assertEqual(json.loads(self.output.read_text())["services"]["codex"],
                         dict(self.codex.return_value, last_attempt_at=quota.iso_from_epoch(300)))


class HttpTests(unittest.TestCase):
    def test_config_page_served_without_auth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            output.write_text("{}")
            server = quota.QuotaServer(("127.0.0.1", 0), quota.make_handler())
            server.snapshot = output
            server.token = "test-secret"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/config?endpoint=e&token=t"
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("text/html", response.headers.get("Content-Type", ""))
                    body = response.read().decode()
                self.assertIn("pebblejs://close#", body)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_watch_endpoint_requires_bearer_token(self) -> None:
        snapshot = {
            "collected_at": "1970-01-01T00:00:00Z",
            "services": {"claude": {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            output.write_text(json.dumps(snapshot))
            server = quota.QuotaServer(("127.0.0.1", 0), quota.make_handler())
            server.snapshot = output
            server.token = "test-secret"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/v1/watch"
            try:
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(url, timeout=2)
                self.assertEqual(denied.exception.code, 401)
                denied.exception.close()

                request = urllib.request.Request(
                    url,
                    headers={"Authorization": "Bearer test-secret"},
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.load(response)
                self.assertEqual(payload["v"], 1)

                with self.assertRaises(urllib.error.HTTPError) as unknown:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{server.server_port}/nope", timeout=2
                    )
                self.assertEqual(unknown.exception.code, 404)
                unknown.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, *args: object) -> bytes:
        return self._body


def _urlopen_returning(payload: object):
    return lambda *args, **kwargs: _FakeResponse(payload)


class TemperatureTests(unittest.TestCase):
    NOW = 1_800_000_000
    STATE: ClassVar[dict[str, Any]] = {
        "state": "sunny", "last_updated": "2027-01-15T08:00:00Z",
        "attributes": {"temperature": 22.2, "temperature_unit": "°C"},
    }

    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ, {
            "HASS_TOKEN": "test-token", "HASS_SERVER": "http://ha.invalid",
        }, clear=True))
        self.enterContext(mock.patch.object(quota.time, "time", return_value=self.NOW))
        self.urlopen = self.enterContext(mock.patch.object(
            quota, "provider_urlopen", return_value=_FakeResponse(self.STATE)))

    def test_supported_units_and_rounding(self) -> None:
        for unit, value, expected in (
            ("°C", 22.2, 222), ("°C", -5.35, -54), ("°C", 0, 0),
            ("°F", 32, 0), ("°F", 68, 200), ("°F", -40, -400), ("°F", 72, 222),
        ):
            with self.subTest(unit=unit, value=value):
                self.urlopen.return_value = _FakeResponse({
                    **self.STATE,
                    "attributes": {"temperature": value, "temperature_unit": unit},
                })
                self.assertEqual(quota.collect_temperature(), expected)
        self.assertEqual(self.urlopen.call_args.args[0].full_url,
                         "http://ha.invalid/api/states/weather.forecast_koti")
        self.assertEqual(self.urlopen.call_args.kwargs["timeout"], 5)

    def test_missing_token_returns_none_without_request(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(quota.collect_temperature())
        self.urlopen.assert_not_called()

    def test_missing_or_unknown_units_are_omitted(self) -> None:
        for unit in (None, "K", "C", "F", "", [], {}):
            with self.subTest(unit=unit):
                attributes = {"temperature": 22.2}
                if unit is not None:
                    attributes["temperature_unit"] = unit
                self.urlopen.return_value = _FakeResponse({**self.STATE, "attributes": attributes})
                self.assertIsNone(quota.collect_temperature())

    def test_invalid_values_are_omitted(self) -> None:
        for value in (None, "22.2", "unknown", True, [], {}, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.urlopen.return_value = _FakeResponse({
                    **self.STATE,
                    "attributes": {"temperature": value, "temperature_unit": "°C"},
                })
                self.assertIsNone(quota.collect_temperature())

    def test_entity_age_boundaries_and_timezone_offsets(self) -> None:
        for age, expected in ((0, 222), (7200, 222), (7200.001, None), (-0.001, None)):
            with self.subTest(age=age):
                self.urlopen.return_value = _FakeResponse({
                    **self.STATE, "last_updated": quota.iso_from_epoch(self.NOW - age),
                })
                self.assertEqual(quota.collect_temperature(), expected)
        self.urlopen.return_value = _FakeResponse({
            **self.STATE, "last_updated": "2027-01-15T10:00:00+02:00",
            "last_changed": "2020-01-01T00:00:00Z",
        })
        self.assertEqual(quota.collect_temperature(), 222)

    def test_missing_or_invalid_time_has_no_fallback(self) -> None:
        for updated in (None, "", "bad", "2027-01-15T08:00:00", self.NOW, []):
            with self.subTest(updated=updated):
                state = {**self.STATE, "last_changed": self.STATE["last_updated"],
                         "last_reported": self.STATE["last_updated"]}
                state.pop("last_updated")
                if updated is not None:
                    state["last_updated"] = updated
                self.urlopen.return_value = _FakeResponse(state)
                self.assertIsNone(quota.collect_temperature())

    def test_unavailable_or_malformed_entities_are_omitted(self) -> None:
        states = [None, [], {}, *({**self.STATE, "state": state}
                  for state in (None, "unknown", "unavailable")),
                  *({**self.STATE, "attributes": attrs} for attrs in (None, [], {}, {"humidity": 44}))]
        for state in states:
            with self.subTest(state=state):
                self.urlopen.return_value = _FakeResponse(state)
                self.assertIsNone(quota.collect_temperature())

    def test_ha_errors_preserve_quota_delivery(self) -> None:
        claude = {"windows": {"5h": {
            "used_fraction": 0.2, "resets_at": self.NOW + 100, "duration_seconds": 100,
        }}}
        self.enterContext(mock.patch.object(quota, "collect_claude", return_value=claude))
        self.enterContext(mock.patch.object(quota, "collect_codex", return_value={"windows": {}}))
        for error in (urllib.error.URLError("connection refused"), TimeoutError("HA slow"),
                      urllib.error.HTTPError("http://ha.invalid", 401, "Unauthorized", Message(), None),
                      json.JSONDecodeError("invalid JSON", "bad", 0)):
            with self.subTest(error=type(error).__name__):
                if isinstance(error, urllib.error.HTTPError):
                    self.addCleanup(error.close)
                self.urlopen.side_effect = error
                data = quota.collect_all({"temperature_c_tenths": 999})
                self.assertTrue(quota.has_quota_data(data))
                self.assertNotIn("temperature_c_tenths", data)
                compact = quota.compact_watch(data, now=self.NOW)
                self.assertNotIn("t", compact)
                self.assertEqual(len(compact["q"]), 1)
                self.assertIn(type(error).__name__, data["temperature_error"])

    def test_stale_reading_does_not_retain_previous_temperature(self) -> None:
        self.urlopen.return_value = _FakeResponse({
            **self.STATE, "last_updated": quota.iso_from_epoch(self.NOW - 7201),
        })
        with (
            mock.patch.object(quota, "collect_claude", return_value={"windows": {}}),
            mock.patch.object(quota, "collect_codex", return_value={"windows": {}}),
        ):
            data = quota.collect_all({"temperature_c_tenths": 999})
        self.assertNotIn("temperature_c_tenths", data)
        self.assertNotIn("temperature_error", data)


class CollectAllTemperatureTests(unittest.TestCase):
    def test_temperature_recorded_when_available(self) -> None:
        with mock.patch.object(quota, "collect_claude", return_value={"windows": {}}), \
             mock.patch.object(quota, "collect_codex", return_value={"windows": {}}), \
             mock.patch.object(quota, "collect_temperature", return_value=222):
            data = quota.collect_all()
        self.assertEqual(data["temperature_c_tenths"], 222)
        self.assertNotIn("temperature_error", data)

    def test_partial_failure_keeps_quota_and_omits_temperature(self) -> None:
        claude = {"windows": {"5h": {
            "used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100,
        }}}

        def boom() -> int:
            raise TimeoutError("HA slow")

        with mock.patch.object(quota, "collect_claude", return_value=claude), \
             mock.patch.object(quota, "collect_codex", return_value={"windows": {}}), \
             mock.patch.object(quota, "collect_temperature", side_effect=boom):
            data = quota.collect_all()
        # Quota survives the temperature outage.
        self.assertTrue(quota.has_quota_data(data))
        self.assertNotIn("temperature_c_tenths", data)
        self.assertIn("TimeoutError", data["temperature_error"])

    def test_compact_watch_includes_temperature(self) -> None:
        data = {
            "collected_at": 0,
            "temperature_c_tenths": 222,
            "services": {"claude": {"windows": {"5h": {
                "used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100,
            }}}},
        }
        self.assertEqual(quota.compact_watch(data, now=950)["t"], 222)

    def test_compact_watch_omits_absent_temperature(self) -> None:
        data = {"collected_at": 0, "services": {"claude": {"windows": {}}}}
        self.assertNotIn("t", quota.compact_watch(data, now=0))


class ClaudeCollectTests(unittest.TestCase):
    LIMITS: ClassVar[list[dict[str, Any]]] = [
        {"kind": "session", "percent": 5,
         "resets_at": "2026-08-03T22:59:59+00:00", "scope": None},
        {"kind": "weekly_all", "percent": 40,
         "resets_at": "2026-08-10T12:59:59+00:00", "scope": None},
        {"kind": "weekly_scoped", "percent": 55,
         "resets_at": "2026-08-10T12:59:59+00:00",
         "scope": {"model": {"display_name": "Fable"}}},
    ]

    def _collect(self, payload: object) -> dict:
        with tempfile.TemporaryDirectory() as home:
            credentials = home + "/.claude/.credentials.json"
            Path(home, ".claude").mkdir(parents=True)
            Path(credentials).write_text(json.dumps(
                {"claudeAiOauth": {"accessToken": "test-token"}}))
            with mock.patch.dict(os.environ, {"HOME": home}), mock.patch.object(
                quota, "provider_urlopen", _urlopen_returning(payload)
            ):
                return quota.collect_claude()

    def test_limits_percentages(self) -> None:
        for percent, expected in ((0, 0.0), (1, 0.01), (100, 1.0)):
            with self.subTest(percent=percent):
                result = self._collect({"limits": [
                    {**limit, "percent": percent} for limit in self.LIMITS
                ]})
                self.assertEqual(set(result["windows"]), {"5h", "7d", "7d (Fable)"})
                for window in result["windows"].values():
                    self.assertEqual(window["used_fraction"], expected)

    def test_legacy_percentages(self) -> None:
        for percent, expected in ((0, 0.0), (1, 0.01), (100, 1.0)):
            with self.subTest(percent=percent):
                result = self._collect({
                    name: {"utilization": percent, "resets_at": "2026-08-10T12:00:00+00:00"}
                    for name in ("five_hour", "seven_day")
                })
                self.assertEqual(set(result["windows"]), {"5h", "7d"})
                for window in result["windows"].values():
                    self.assertEqual(window["used_fraction"], expected)

    def test_limits_are_preferred_and_include_fable(self) -> None:
        result = self._collect({
            "five_hour": {"utilization": 1.0, "resets_at": "2026-08-03T22:00:00+00:00"},
            "seven_day": {"utilization": 2.0, "resets_at": "2026-08-10T12:00:00+00:00"},
            "limits": self.LIMITS,
        })
        self.assertEqual(list(result["windows"]), ["5h", "7d", "7d (Fable)"])
        self.assertEqual(result["windows"]["7d (Fable)"]["used_fraction"], 0.55)
        self.assertEqual(
            result["windows"]["7d (Fable)"]["duration_seconds"], 604_800)

    def test_legacy_pair_is_the_fallback(self) -> None:
        result = self._collect({
            "five_hour": {"utilization": 5.0, "resets_at": "2026-08-03T22:00:00+00:00"},
            "seven_day": {"utilization": 40.0, "resets_at": "2026-08-10T12:00:00+00:00"},
        })
        self.assertEqual(list(result["windows"]), ["5h", "7d"])
        self.assertEqual(result["windows"]["5h"]["used_fraction"], 0.05)

    def test_scoped_window_without_reset_is_dropped(self) -> None:
        limits = self.LIMITS + [
            {"kind": "weekly_scoped", "percent": 0, "resets_at": None,
             "scope": {"model": {"display_name": "Opus"}}},
        ]
        result = self._collect({"limits": limits})
        self.assertEqual(list(result["windows"]), ["5h", "7d", "7d (Fable)"])


class SecurityTests(unittest.TestCase):
    def test_guards_block_real_network_credentials_and_processes(self):
        with self.assertRaises(LiveAccessError):
            urllib.request.urlopen("https://provider.invalid/", timeout=1)
        with self.assertRaises(LiveAccessError):
            Path("/home/agent/.claude/.credentials.json").read_text()
        with self.assertRaises(LiveAccessError):
            quota.collect_codex()
        with self.assertRaises(LiveAccessError), \
             mock.patch.object(quota, "collect_claude", side_effect=LiveAccessError("blocked")):
            quota.collect_all()

    def test_snapshot_is_private_and_does_not_follow_fixed_temp_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            victim = Path(directory) / "victim"
            victim.write_text("untouched")
            output.with_suffix(".json.tmp").symlink_to(victim)
            old_umask = os.umask(0o022)
            try:
                for value in (1, 2):
                    quota.write_snapshot({"value": value}, output)
                    self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            finally:
                os.umask(old_umask)
            self.assertEqual(victim.read_text(), "untouched")
            self.assertEqual(json.loads(output.read_text()), {"value": 2})
            with mock.patch.object(quota.os, "replace", side_effect=OSError("disk full")), \
                 self.assertRaises(OSError):
                quota.write_snapshot({}, output)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),
                             ["latest.json", "latest.json.tmp", "victim"])

    def test_codex_fake_receives_only_allowlisted_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            fake = home / "codex"
            fake.write_text("#!" + sys.executable + "\n" +
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['HOME'], 'env.json').write_text(json.dumps(dict(os.environ)))\n"
                "for line in sys.stdin:\n"
                "    request = json.loads(line)\n"
                "    if request.get('id') == 1:\n"
                "        print(json.dumps({'id': 1, 'result': {'userAgent': 'fake'}}), flush=True)\n"
                "    elif 'id' in request:\n"
                "        print(json.dumps({'id': request['id'], 'result': {'primary': "
                "{'usedPercent': 20, 'windowDurationMins': 300, 'resetsAt': 18000}}}), flush=True)\n")
            fake.chmod(0o700)
            env = {"HOME": directory, "PATH": directory, "CODEX_HOME": directory,
                   "TERM": "dumb", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                   "HTTPS_PROXY": "http://fake.invalid", "PEBBLE_QUOTA_TOKEN": "fake",
                   "HASS_TOKEN": "fake", "OPENAI_API_KEY": "fake", "OTHER_SECRET": "fake", "LC_API_KEY": "fake"}
            def fake_codex(*args, **kwargs):
                process = _REAL_POPEN(*args, **kwargs)
                assert process.stdin and process.stdout
                self.addCleanup(process.stdin.close)
                self.addCleanup(process.stdout.close)
                return process

            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
                    quota.subprocess, "Popen", fake_codex):
                result = quota.collect_codex()
            self.assertEqual(result["windows"]["5h"]["used_fraction"], .2)
            child_env = json.loads((home / "env.json").read_text())
            self.assertEqual(set(child_env), (set(env) | {"SHELL"}) -
                             {"PEBBLE_QUOTA_TOKEN", "HASS_TOKEN", "OPENAI_API_KEY", "OTHER_SECRET", "LC_API_KEY"})

    def test_build_and_clean_scrub_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "pebble"
            fake.write_text("#!" + sys.executable + "\n" +
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(sys.argv[1] + '.json').write_text(json.dumps(dict(os.environ)))\n")
            fake.chmod(0o700)
            makefile = Path(__file__).parents[1] / "watchface/Makefile"
            env = {"HOME": directory, "PATH": directory + os.pathsep + _TOOL_PATH,
                   "LANG": "C.UTF-8", "HASS_TOKEN": "fake", "BUILD_API_KEY": "fake"}
            make = shutil.which("make", path=_TOOL_PATH)
            bash = shutil.which("bash", path=_TOOL_PATH)
            assert make and bash
            with mock.patch.object(subprocess, "Popen", _REAL_POPEN):
                subprocess.run([make, "-f", str(makefile), "SHELL=" + bash, "clean", "build"],
                               cwd=directory, env=env, check=True, capture_output=True)
            for command in ("clean", "build"):
                captured = json.loads((root / (command + ".json")).read_text())
                self.assertEqual(set(captured), {"HOME", "PATH", "LANG", "CC"})

    def test_provider_redirects_are_refused(self):
        seen = []

        class Redirect(quota.BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.headers.get("Authorization"))
                self.send_response(302)
                self.send_header("Location", "http://other-provider.invalid/stolen")
                self.end_headers()

            def log_message(self, *args):
                pass

        server = quota.ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".claude").mkdir()
            (home / ".claude/.credentials.json").write_text(
                json.dumps({"claudeAiOauth": {"accessToken": "fake"}}))
            with mock.patch.dict(os.environ, {"HOME": directory, "HASS_TOKEN": "fake",
                                              "HASS_SERVER": url}), mock.patch.object(
                    quota, "CLAUDE_USAGE_URL", url):
                for collector in (quota.collect_claude, quota.collect_temperature):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        collector()
                    self.assertEqual(error.exception.code, 302)
                    error.exception.close()
        self.assertEqual(seen, ["Bearer fake", "Bearer fake"])
        handler = quota.NoProviderRedirect()
        for destination in ("https://other.invalid/", "http://origin.invalid/"):
            self.assertIsNone(handler.redirect_request(
                urllib.request.Request("https://origin.invalid/"), None, 302,
                "Found", {}, destination))

    def test_503_does_not_reflect_exception_in_response(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            output.write_text(json.dumps({"collected_at": "bad\r\nInjected: yes ☃"}))
            server = quota.QuotaServer(("127.0.0.1", 0), quota.make_handler())
            server.snapshot, server.token = output, "fake"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/v1/watch",
                    headers={"Authorization": "Bearer fake"})
                with mock.patch.object(quota.sys, "stderr", new_callable=io.StringIO) as log:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(request, timeout=2)
                    self.assertEqual(error.exception.code, 503)
                    self.assertEqual(error.exception.reason, "Snapshot unavailable")
                    self.assertNotIn("Injected", error.exception.read().decode())
                    self.assertIsNone(error.exception.headers.get("Injected"))
                    error.exception.close()
                    self.assertIn("ValueError", log.getvalue())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


class StartupTests(unittest.TestCase):
    def test_busy_port_does_not_collect(self):
        server = quota.QuotaServer(("127.0.0.1", 0), quota.make_handler())
        self.addCleanup(server.server_close)
        with mock.patch.dict(os.environ, {"PEBBLE_QUOTA_TOKEN": "fake"}), mock.patch.object(
                sys, "argv", ["quota", "serve", "--port", str(server.server_port)]), mock.patch.object(
                quota, "collect_all") as collect:
            with self.assertRaises(OSError):
                quota.main()
            collect.assert_not_called()

    def test_restarts_honour_persisted_attempts_including_total_failure(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "latest.json"
                with mock.patch.object(quota, "utc_iso", return_value=quota.iso_from_epoch(1000)), \
                     mock.patch.object(quota, "collect_claude") as claude, \
                     mock.patch.object(quota, "collect_codex") as codex, \
                     mock.patch.object(quota, "collect_temperature", return_value=None):
                    for collector in (claude, codex):
                        if failed:
                            collector.side_effect = RuntimeError("offline")
                        else:
                            collector.return_value = {"windows": {"5h": {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}}}
                    for _ in range(2):
                        try:
                            quota.refresh_snapshot(output, interval_seconds=300)
                        except RuntimeError:
                            self.assertTrue(failed)
                    self.assertEqual(claude.call_count, 1)
                    self.assertEqual(codex.call_count, 1)
                    state = json.loads(output.read_text())
                    for service in state["services"].values():
                        self.assertEqual(service["last_attempt_at"], quota.iso_from_epoch(1000))

    def test_write_failure_keeps_429_in_memory_and_waits_between_attempts(self):
        stop = mock.Mock()
        stop.is_set.return_value = False
        stop.wait.side_effect = [False, False, True]
        times = iter((1000, 1000, 1300, 1600, 1600))
        error = urllib.error.HTTPError("https://fake.invalid", 429, "limited", Message(), None)
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(quota, "utc_iso", side_effect=lambda: quota.iso_from_epoch(next(times))), \
             mock.patch.object(quota, "collect_claude", side_effect=error) as claude, \
             mock.patch.object(quota, "collect_codex", return_value={"windows": {}}) as codex, \
             mock.patch.object(quota, "collect_temperature", return_value=None), \
             mock.patch.object(quota, "write_snapshot", side_effect=OSError("disk full")), \
             mock.patch.object(quota.sys, "stderr", new_callable=io.StringIO):
            quota.refresh_forever(Path(directory) / "latest.json", 200, stop)
        self.assertEqual(claude.call_count, 2)
        self.assertEqual(codex.call_count, 3)
        self.assertEqual(stop.wait.call_args_list, [mock.call(200)] * 3)


class ValidationTests(unittest.TestCase):
    WINDOW: ClassVar[dict[str, Any]] = {"used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100}

    def snapshot(self, windows=None, name="claude"):
        return {"collected_at": quota.iso_from_epoch(0), "services": {
            name: {"windows": {"5h": self.WINDOW} if windows is None else windows}}}

    def test_bad_windows_are_rejected_individually_for_both_providers(self):
        invalid = [None, [], {}, {"used": 1}]
        for field, values in {
            "used_fraction": [None, True, "0.2", float("nan"), float("inf"),
                              -float("inf"), -0.01, 1.01, 10**400],
            "resets_at": [None, True, [], {}, "1000", "bad", "2026-10-22",
                          "2026-10-22T00:00:00", float("nan"), float("inf"),
                          -1, 1.5, quota.WATCH_INT_MAX + 1],
            "duration_seconds": [None, True, "100", 0, -1, 1.5, float("nan"),
                                 float("inf"), quota.MAX_DURATION_SECONDS + 1],
        }.items():
            invalid.extend(dict(self.WINDOW, **{field: value}) for value in values)
            invalid.append({key: value for key, value in self.WINDOW.items() if key != field})
        for name in ("claude", "codex"):
            for window in invalid:
                with self.subTest(name=name, window=window):
                    data = self.snapshot({"5h": self.WINDOW, "7d": window}, name)
                    self.assertTrue(quota.has_quota_data(data))
                    rows = quota.compact_watch(data, now=950)["q"]
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["w"], "5h")
                    self.assertFalse(quota.has_quota_data(self.snapshot({"7d": window}, name)))

    def test_shapes_labels_and_watch_bounds(self):
        for data in (None, [], [1], "bad", {}, {"services": []},
                     {"services": {"claude": []}},
                     self.snapshot([]), self.snapshot({"5h": []})):
            with self.subTest(data=data):
                self.assertFalse(quota.has_quota_data(data))
                self.assertEqual(quota.compact_watch(data)["q"], [])
        for label in ("", "12345678", "é", "bad\n", 5):
            self.assertFalse(quota.has_quota_data(self.snapshot({label: self.WINDOW})))
        for used in (0, 1):
            data = self.snapshot({"1234567": dict(self.WINDOW, used_fraction=used,
                resets_at=quota.WATCH_INT_MAX, duration_seconds=quota.MAX_DURATION_SECONDS)})
            self.assertTrue(quota.has_quota_data(data))
            json.dumps(quota.compact_watch(data), allow_nan=False)
        for percent in ("20", True, float("nan"), float("inf"), -1, 101):
            self.assertIsNone(quota.percent_fraction(percent))

    def test_claude_malformed_scopes_and_duplicate_windows(self):
        good = {"kind": "session", "percent": 20, "resets_at": 1000}
        malformed = [None, [], {}, {"kind": []}, dict(good, percent="20"),
                     dict(good, resets_at="bad"), dict(good, scope=[])]
        for scope in (None, [], "bad", {"model": []}, {"model": {}},
                      {"model": {"display_name": []}},
                      {"model": {"display_name": "Unknown"}}):
            malformed.append(dict(good, kind="weekly_scoped", scope=scope))
        self.assertEqual(quota.claude_windows_from_limits([good, *malformed]),
                         {"5h": dict(self.WINDOW, duration_seconds=18000)})
        for limits in (1, "bad", {"kind": "session"}):
            self.assertEqual(quota.claude_windows_from_limits(limits), {})

    def test_damaged_disk_state_cannot_block_healthy_collection(self):
        states = [None, "{broken", "[1]", "null", '"bad"', '{"services": []}',
                  ('{"services": {"claude": {"last_attempt_at": [], "retry_at": {},'
                   '"rate_limit_failures": "bad", "windows": []}, "codex": []}}')]
        for state in states:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "latest.json"
                if state is not None:
                    output.write_text(state)
                with mock.patch.object(quota, "collect_claude", return_value={"windows": {}}) as claude, \
                     mock.patch.object(quota, "collect_codex", return_value={"windows": {"5h": self.WINDOW}}) as codex, \
                     mock.patch.object(quota, "collect_temperature", return_value=None):
                    result = quota.refresh_snapshot(output, interval_seconds=300)
                claude.assert_called_once()
                codex.assert_called_once()
                self.assertTrue(quota.has_quota_data(result))

    def test_invalid_refresh_retains_good_codex_and_first_429_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            good = self.snapshot(name="codex")
            quota.write_snapshot(good, output)
            error = urllib.error.HTTPError("https://fake.invalid", 429, "secret", Message(), None)
            with mock.patch.object(quota, "utc_iso", return_value=quota.iso_from_epoch(300)), \
                 mock.patch.object(quota, "collect_claude", side_effect=error) as claude, \
                 mock.patch.object(quota, "collect_codex", return_value={"windows": {"5h": {"used": 1}}}) as codex, \
                 mock.patch.object(quota, "collect_temperature", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "preserving previous"):
                    quota.refresh_snapshot(output, interval_seconds=300)
                self.assertEqual(json.loads(output.read_text())["collected_at"], good["collected_at"])
                quota.refresh_snapshot(output, interval_seconds=300)
                claude.assert_called_once()
                codex.assert_called_once()
            saved = json.loads(output.read_text())
            self.assertEqual(saved["services"]["codex"]["windows"], good["services"]["codex"]["windows"])
            self.assertEqual(quota.epoch(saved["services"]["claude"]["retry_at"]), 900)
            self.assertNotIn("secret", output.read_text())

    def test_all_invalid_refresh_over_good_state_retains_quota(self):
        for name in ("claude", "codex"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "latest.json"
                good = self.snapshot(name=name)
                quota.write_snapshot(good, output)
                invalid = {"windows": {"5h": dict(self.WINDOW, used_fraction=float("nan"))}}
                with mock.patch.object(quota, "collect_claude", return_value=invalid), \
                     mock.patch.object(quota, "collect_codex", return_value=invalid), \
                     mock.patch.object(quota, "collect_temperature", return_value=None):
                    try:
                        quota.refresh_snapshot(output)
                    except RuntimeError:
                        self.assertEqual(name, "codex")
                saved = json.loads(output.read_text())
                self.assertEqual(saved["services"][name]["windows"], good["services"][name]["windows"])
                self.assertTrue(saved["services"][name]["stale"])
                self.assertEqual(saved["services"][name]["error"], "Invalid quota windows")
                self.assertEqual(len(quota.compact_watch(saved)["q"]), 1)

    def test_both_failed_publishes_retained_claude_but_keeps_whole_codex_snapshot(self):
        claude = {"service": "claude", "error": "HTTPError", "rate_limit_failures": 1,
                  "retry_at": quota.iso_from_epoch(900), "last_attempt_at": quota.iso_from_epoch(300)}
        codex = {"service": "codex", "error": "RuntimeError", "last_attempt_at": quota.iso_from_epoch(300)}
        retained = {"windows": {"5h": self.WINDOW}, "last_success_at": quota.iso_from_epoch(0),
                    "stale": True, "age_seconds": 300}
        expected = {
            "claude": (300, 111, {"claude": dict(claude, **retained), "codex": codex}),
            "codex": (0, 222, {"claude": claude, "codex": dict(codex, **retained)}),
        }
        for name, (at, tenths, services) in expected.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "latest.json"
                quota.write_snapshot(dict(self.snapshot(name=name), temperature_c_tenths=222), output)
                error = urllib.error.HTTPError("https://fake.invalid", 429, "secret", Message(), None)
                with mock.patch.object(quota, "utc_iso", return_value=quota.iso_from_epoch(300)), \
                     mock.patch.object(quota, "collect_claude", side_effect=error), \
                     mock.patch.object(quota, "collect_codex", side_effect=RuntimeError("offline")), \
                     mock.patch.object(quota, "collect_temperature", return_value=111):
                    if name == "codex":
                        with self.assertRaisesRegex(RuntimeError, "preserving previous"):
                            quota.refresh_snapshot(output, interval_seconds=300)
                    else:
                        quota.refresh_snapshot(output, interval_seconds=300)
                saved = json.loads(output.read_text())
                self.assertEqual(saved, {"collected_at": quota.iso_from_epoch(at), "services": services,
                                         "temperature_c_tenths": tenths})
                code = "C" if name == "claude" else "X"
                self.assertEqual(quota.compact_watch(saved, now=950), {"v": 1, "at": at, "q": [
                    {"s": code, "w": "5h", "u": 20, "r": 1000, "d": 100, "p": 30}], "t": tenths})

    def test_first_429_without_rows_is_unavailable_but_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            error = urllib.error.HTTPError("https://fake.invalid", 429, "secret", Message(), None)
            with mock.patch.object(quota, "utc_iso", return_value=quota.iso_from_epoch(300)), \
                 mock.patch.object(quota, "collect_claude", side_effect=error) as claude, \
                 mock.patch.object(quota, "collect_codex", side_effect=RuntimeError("secret")) as codex, \
                 mock.patch.object(quota, "collect_temperature", return_value=None):
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "no snapshot available"):
                        quota.refresh_snapshot(output, interval_seconds=300)
                claude.assert_called_once()
                codex.assert_called_once()
            self.assertEqual(json.loads(output.read_text()), {"services": {
                "claude": {"service": "claude", "error": "HTTPError", "rate_limit_failures": 1,
                           "retry_at": quota.iso_from_epoch(900), "last_attempt_at": quota.iso_from_epoch(300)},
                "codex": {"service": "codex", "error": "RuntimeError", "last_attempt_at": quota.iso_from_epoch(300)},
            }})

    def test_atomic_replace_failure_leaves_good_disk_and_new_memory_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            good = self.snapshot()
            quota.write_snapshot(good, output)
            original = output.read_bytes()
            state = dict(good)
            failed = {"services": {"claude": {"retry_at": quota.iso_from_epoch(900),
                                             "error": "HTTPError"}}}
            with mock.patch.object(quota, "collect_all", return_value=failed), \
                 mock.patch.object(quota.os, "replace", side_effect=OSError("secret")), \
                 self.assertRaises(OSError):
                quota.refresh_snapshot(output, state)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(quota.epoch(state["services"]["claude"]["retry_at"]), 900)
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_http_damaged_state_and_diagnostics_are_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latest.json"
            server = quota.QuotaServer(("127.0.0.1", 0), quota.make_handler())
            server.snapshot, server.token = output, "fake"
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/watch",
                                             headers={"Authorization": "Bearer fake"})
            try:
                states = [
                    (None, "Quota unavailable"),
                    ("{secret", "JSONDecodeError"),
                    ("[1]", "ValueError"),
                    ('{"services": []}', "ValueError"),
                    (json.dumps(self.snapshot({"5h": {"used": 1}})), "ValueError"),
                    ('{"services": {"claude": {"retry_at": "secret"}}}', "ValueError"),
                ]
                for timestamp in (None, True, -1, 1.5, "secret", "2026-10-22",
                                  float("nan"), float("inf"), quota.WATCH_INT_MAX + 1):
                    states.append((json.dumps(dict(self.snapshot(), collected_at=timestamp)),
                                   "ValueError"))
                states.append((json.dumps({"services": self.snapshot()["services"]}), "ValueError"))
                fixed_body = None
                for state, category in states:
                    with self.subTest(state=state):
                        if state is not None:
                            output.write_text(state)
                        with mock.patch.object(quota.sys, "stderr", new_callable=io.StringIO) as log:
                            with self.assertRaises(urllib.error.HTTPError) as error:
                                urllib.request.urlopen(request, timeout=2)
                            self.assertEqual(error.exception.code, 503)
                            body = error.exception.read()
                            error.exception.close()
                            if fixed_body is None:
                                fixed_body = body
                            self.assertEqual(body, fixed_body)
                            self.assertIn(b"Snapshot unavailable", body)
                            self.assertNotIn(b"secret", body)
                            self.assertEqual(log.getvalue(), f"snapshot response failed: {category}\n")
                expected_rows = [
                    {"s": "C", "w": "5h", "u": 20, "r": 1000, "d": 100, "p": 30},
                    {"s": "F", "w": "7d", "u": 12, "r": 1000, "d": 100, "p": 38},
                    {"s": "C", "w": "extra", "u": 20, "r": 1000, "d": 100, "p": 30},
                    {"s": "X", "w": "5h", "u": 20, "r": 1000, "d": 100, "p": 30},
                    {"s": "X", "w": "7d", "u": 20, "r": 1000, "d": 100, "p": 30},
                ]
                valid = self.snapshot({
                    "5h": self.WINDOW,
                    "7d (Fable)": dict(self.WINDOW, used_fraction=0.125),
                    "extra": self.WINDOW,
                })
                valid["services"]["codex"] = {"windows": {
                    "5h": self.WINDOW, "7d": self.WINDOW, "last": self.WINDOW}}
                valid["temperature_c_tenths"] = 222
                for timestamp in (0, "1970-01-01T00:00:00.999Z", 42):
                    for mixed in (False, True):
                        with self.subTest(timestamp=timestamp, mixed=mixed):
                            data: dict[str, Any] = json.loads(json.dumps(valid))
                            data["collected_at"] = timestamp
                            if mixed:
                                for service in data["services"].values():
                                    service["windows"]["bad"] = {"used": 1}
                            output.write_text(json.dumps(data))
                            with (mock.patch.object(quota.time, "time", return_value=950),
                                  urllib.request.urlopen(request, timeout=2) as response):
                                self.assertEqual(response.status, 200)
                                self.assertEqual(response.headers["Content-Type"], "application/json")
                                self.assertEqual(response.headers["Cache-Control"], "no-store")
                                payload = json.load(response)
                            self.assertEqual(payload, {"v": 1, "at": 42 if timestamp == 42 else 0,
                                                       "q": expected_rows, "t": 222})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


class CodexResultTests(unittest.TestCase):
    WINDOW: ClassVar[dict] = {"usedPercent": 1, "resetsAt": 1000, "windowDurationMins": 300}

    def test_codex_malformed_primary_does_not_block_secondary(self):
        good = {"usedPercent": 20, "resetsAt": 1000, "windowDurationMins": 300}
        for primary in (None, [], "bad", {}, dict(good, resetsAt="bad"),
                        dict(good, usedPercent="20"), dict(good, windowDurationMins=[])):
            with self.subTest(primary=primary):
                data = quota.codex_service_from_result({
                    "rateLimits": {"primary": primary, "secondary": good}})
                self.assertEqual(data["windows"], {"5h": {
                    "used_fraction": .2, "resets_at": 1000, "duration_seconds": 18000}})

    def test_formats_and_percentages(self):
        for wrapped in (False, True):
            for used in (0, .5, 1, 2, 100):
                with self.subTest(wrapped=wrapped, used=used):
                    limits = {"primary": dict(self.WINDOW, usedPercent=used)}
                    result = {"rateLimits": limits} if wrapped else limits
                    self.assertEqual(quota.codex_service_from_result(result), {
                        "service": "codex", "windows": {"5h": {
                            "used_fraction": used / 100, "resets_at": 1000,
                            "duration_seconds": 18000}}})

    def test_duration_bounds_and_labels(self):
        maximum = quota.MAX_DURATION_SECONDS // 60
        for minutes, label in ((1, "1m"), (60, "60m"), (300, "5h"),
                               (10080, "7d"), (maximum, f"{maximum}m")):
            with self.subTest(minutes=minutes):
                data = quota.codex_service_from_result({
                    "primary": dict(self.WINDOW, windowDurationMins=minutes)})
                self.assertEqual(list(data["windows"]), [label])
                self.assertEqual(data["windows"][label]["duration_seconds"], minutes * 60)
        for minutes in (0, -1, maximum + 1, True, 300.0, "300", None, []):
            with self.subTest(minutes=minutes), self.assertRaisesRegex(
                    quota.CodexError, "^Codex rate limits: invalid result$"):
                quota.codex_service_from_result({
                    "primary": dict(self.WINDOW, windowDurationMins=minutes)})

    def test_window_order_and_duplicate_duration(self):
        secondary = dict(self.WINDOW, usedPercent=2)
        data = quota.codex_service_from_result({"secondary": secondary,
            "primary": dict(self.WINDOW, windowDurationMins=10080)})
        self.assertEqual(list(data["windows"]), ["7d", "5h"])
        data = quota.codex_service_from_result({"primary": self.WINDOW, "secondary": secondary})
        self.assertEqual(list(data["windows"]), ["5h"])
        self.assertEqual(data["windows"]["5h"]["used_fraction"], .02)

    def test_invalid_results_and_missing_usage(self):
        missing = {key: value for key, value in self.WINDOW.items() if key != "usedPercent"}
        for result in (None, [], "bad", {}, {"userAgent": []}, {"rateLimits": None},
                       {"rateLimits": []}, {"primary": []}, {"primary": missing},
                       {"primary": dict(self.WINDOW, usedPercent="bad")},
                       {"rateLimits": None, "primary": self.WINDOW}):
            with self.subTest(result=result):
                with self.assertRaises(quota.CodexError) as caught:
                    quota.codex_service_from_result(result)
                self.assertEqual(quota.diagnostic(caught.exception), "Codex rate limits: invalid result")

    def test_explicit_no_windows(self):
        for result in ({"rateLimits": {}}, {"rateLimits": {"primary": None, "secondary": None}},
                       {"primary": None, "secondary": None}):
            with self.subTest(result=result):
                self.assertEqual(quota.codex_service_from_result(result), {
                    "service": "codex", "windows": {},
                    "error": "Codex rate limits: no quota windows"})


class CodexRPCTests(unittest.TestCase):
    INITIALIZE: ClassVar[dict] = {"id": 1, "result": {"userAgent": "fake-app-server"}}
    WINDOW: ClassVar[dict] = {"usedPercent": 1, "resetsAt": 1000, "windowDurationMins": 300}

    @contextlib.contextmanager
    def server(self, replies, *, ignore_terminate=False):
        """Run only a generated fixture, never a PATH-resolved provider CLI."""
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "app_server.py"
            fake.write_text(
                "import json, signal, sys\n"
                + ("signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if ignore_terminate else "")
                + "replies = " + repr(replies) + "\n"
                "for line in sys.stdin:\n"
                "    request = json.loads(line)\n"
                "    if 'id' not in request: continue\n"
                "    output = replies.get(request['id'], [])\n"
                "    if output is None: sys.exit(0)\n"
                "    for response in output:\n"
                "        print(response, flush=True)\n")
            processes = []
            def launch(args, **kwargs):
                self.assertEqual(args, ["codex", "app-server", "--stdio"])
                process = _REAL_POPEN([sys.executable, str(fake)], **kwargs)
                processes.append(process)
                return process

            with mock.patch.object(quota.subprocess, "Popen", side_effect=launch), \
                 mock.patch.object(quota, "CODEX_RPC_TIMEOUT_SECONDS", .5), \
                 mock.patch.object(quota, "CODEX_EXIT_TIMEOUT_SECONDS", .1):
                try:
                    yield processes
                finally:
                    for process in processes:
                        # Cleanup even when an assertion fails, then report adapter leaks.
                        leaked = process.poll() is None
                        if leaked:
                            process.kill()
                            process.wait()
                        self.assertFalse(leaked, "adapter left fixture running")
                        self.assertIsNotNone(process.returncode)
                        self.assertTrue(process.stdin.closed)
                        self.assertTrue(process.stdout.closed)

    def replies(self, result):
        return {1: [json.dumps(self.INITIALIZE)],
                2: [json.dumps({"id": 2, "result": result})]}

    def assert_failure(self, replies, expected):
        with self.server(replies), self.assertRaises(quota.CodexError) as caught:
            quota.collect_codex()
        self.assertEqual(quota.diagnostic(caught.exception), expected)

    def test_success_notifications_and_compact_percentage(self):
        result = {"rateLimits": {"primary": self.WINDOW,
                  "secondary": dict(self.WINDOW, windowDurationMins=10080)}}
        replies = self.replies(result)
        for responses in replies.values():
            responses.insert(0, json.dumps({"method": "fake/notification",
                                            "params": {"credential": "fixture-only"}}))
        with self.server(replies):
            data = quota.collect_codex()
        self.assertEqual(list(data["windows"]), ["5h", "7d"])
        self.assertEqual(data["windows"]["5h"]["used_fraction"], .01)
        self.assertEqual(quota.compact_watch({"services": {"codex": data}}, now=1000)["q"][0]["u"], 1)

    def test_both_rpc_errors_are_sanitized_and_other_rows_survive(self):
        error = {"code": -32000, "message": "fixture-only", "data": "fixture-only"}
        for request_id, stage in ((1, "initialize"), (2, "rate limits")):
            replies = self.replies({"rateLimits": {}})
            replies[request_id] = [json.dumps({"id": request_id, "error": error})]
            with self.subTest(stage=stage), self.server(replies), \
                 mock.patch.object(quota, "collect_claude", return_value={
                     "windows": {"5h": {"used_fraction": .2, "resets_at": 1000,
                                       "duration_seconds": 18000}}}), \
                 mock.patch.object(quota, "collect_temperature", return_value=None):
                data = quota.collect_all()
                self.assertEqual(data["services"]["codex"]["error"],
                                 f"Codex {stage}: RPC error (check CLI login and compatibility)")
                self.assertEqual(quota.compact_watch(data)["q"][0]["s"], "C")
                self.assertNotIn("fixture-only", json.dumps(data))
                self.assertEqual(quota.normalize_snapshot(data)["services"]["codex"]["error"],
                                 data["services"]["codex"]["error"])

    def test_eof_and_timeout_at_each_stage(self):
        for request_id, stage in ((1, "initialize"), (2, "rate limits")):
            for response, reason in ((None, "unexpected EOF"), ([], "response timeout")):
                with self.subTest(stage=stage, reason=reason):
                    replies = self.replies({"rateLimits": {}})
                    replies[request_id] = response
                    self.assert_failure(replies, f"Codex {stage}: {reason}")

    def test_notifications_without_a_reply_still_time_out(self):
        for request_id, stage in ((1, "initialize"), (2, "rate limits")):
            replies = self.replies({"rateLimits": {}})
            replies[request_id] = [json.dumps({"method": "notice"})] * 20
            with self.subTest(stage=stage):
                self.assert_failure(replies, f"Codex {stage}: response timeout")

    def test_invalid_json_responses_and_results(self):
        for request_id, stage in ((1, "initialize"), (2, "rate limits")):
            cases = [
                ("fixture-only{", "invalid JSON"),
                ("[]", "invalid response"),
                ("{}", "invalid response"),
                (json.dumps({"id": 99, "result": {}}), "invalid response"),
                (json.dumps({"id": True, "result": {}}), "invalid response"),
            ]
            for result in (None, [], "fixture-only", {}, {"userAgent": []}):
                cases.append((json.dumps({"id": request_id, "result": result}), "invalid result"))
            for response, reason in cases:
                with self.subTest(stage=stage, response=response):
                    replies = self.replies({"rateLimits": {}})
                    replies[request_id] = [response]
                    self.assert_failure(replies, f"Codex {stage}: {reason}")

    def test_no_windows_diagnostic_survives_collection(self):
        with self.server(self.replies({"rateLimits": {}})), \
             mock.patch.object(quota, "collect_claude", return_value={"windows": {}}), \
             mock.patch.object(quota, "collect_temperature", return_value=None):
            data = quota.collect_all()
        self.assertEqual(data["services"]["codex"]["error"], "Codex rate limits: no quota windows")

    def test_forced_kill_is_followed_by_wait_and_pipe_cleanup(self):
        import signal
        for replies, fails in ((self.replies({"rateLimits": {}}), False),
                               ({1: []}, True)):
            with self.subTest(fails=fails), self.server(replies, ignore_terminate=True) as processes:
                if fails:
                    with self.assertRaises(quota.CodexError):
                        quota.collect_codex()
                else:
                    quota.collect_codex()
                self.assertEqual(processes[0].returncode, -signal.SIGKILL)

    def test_write_failure_still_reaps_and_closes(self):
        process = mock.Mock(stdin=io.StringIO(), stdout=io.StringIO())
        process.stdin = mock.Mock(wraps=process.stdin)
        process.stdin.write.side_effect = BrokenPipeError("fixture-only")
        with mock.patch.object(quota.subprocess, "Popen", return_value=process), \
             self.assertRaisesRegex(quota.CodexError, "Codex initialize: pipe failure"):
            quota.collect_codex()
        process.wait.assert_called_once()
        process.stdin.close.assert_called_once()
        self.assertTrue(process.stdout.closed)


if __name__ == "__main__":
    unittest.main()
