from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).parents[1] / "collector/pebble_quota.py"
spec = importlib.util.spec_from_file_location("pebble_quota", MODULE_PATH)
assert spec and spec.loader
quota = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quota)


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
            "services": {"claude": {"windows": {"5h": {"used": 1}}}},
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
            "services": {"claude": {"windows": {"5h": {"used": 1}}}},
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
            with mock.patch.object(quota, "collect_all", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "preserving previous"):
                    quota.refresh_snapshot(output)
            self.assertEqual(json.loads(output.read_text()), previous)


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
            "services": {"claude": {"windows": {}}},
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

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, *args: object) -> bytes:
        return self._body


def _urlopen_returning(payload: object):
    return lambda *args, **kwargs: _FakeResponse(payload)


class TemperatureTests(unittest.TestCase):
    STATE = {"state": "sunny", "attributes": {"temperature": 22.2}}

    def test_reads_temperature_as_tenths(self) -> None:
        with mock.patch.dict(os.environ, {"HASS_TOKEN": "t"}, clear=False):
            with mock.patch.object(
                quota.urllib.request, "urlopen", _urlopen_returning(self.STATE)
            ):
                self.assertEqual(quota.collect_temperature(), 222)

    def test_negative_temperature_rounds_to_tenths(self) -> None:
        state = {"state": "cloudy", "attributes": {"temperature": -5.35}}
        with mock.patch.dict(os.environ, {"HASS_TOKEN": "t"}, clear=False):
            with mock.patch.object(
                quota.urllib.request, "urlopen", _urlopen_returning(state)
            ):
                self.assertEqual(quota.collect_temperature(), -54)

    def test_missing_token_returns_none(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "HASS_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsNone(quota.collect_temperature())

    def test_unavailable_state_returns_none(self) -> None:
        state = {"state": "unavailable", "attributes": {}}
        with mock.patch.dict(os.environ, {"HASS_TOKEN": "t"}, clear=False):
            with mock.patch.object(
                quota.urllib.request, "urlopen", _urlopen_returning(state)
            ):
                self.assertIsNone(quota.collect_temperature())

    def test_malformed_state_missing_attribute_returns_none(self) -> None:
        state = {"state": "sunny", "attributes": {"humidity": 44}}
        with mock.patch.dict(os.environ, {"HASS_TOKEN": "t"}, clear=False):
            with mock.patch.object(
                quota.urllib.request, "urlopen", _urlopen_returning(state)
            ):
                self.assertIsNone(quota.collect_temperature())

    def test_network_error_propagates(self) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise urllib.error.URLError("connection refused")

        with mock.patch.dict(os.environ, {"HASS_TOKEN": "t"}, clear=False):
            with mock.patch.object(quota.urllib.request, "urlopen", boom):
                with self.assertRaises(urllib.error.URLError):
                    quota.collect_temperature()


class CollectAllTemperatureTests(unittest.TestCase):
    def test_temperature_recorded_when_available(self) -> None:
        with mock.patch.object(quota, "collect_claude", return_value={"windows": {}}):
            with mock.patch.object(quota, "collect_codex", return_value={"windows": {}}):
                with mock.patch.object(quota, "collect_temperature", return_value=222):
                    data = quota.collect_all()
        self.assertEqual(data["temperature_c_tenths"], 222)
        self.assertNotIn("temperature_error", data)

    def test_partial_failure_keeps_quota_and_omits_temperature(self) -> None:
        claude = {"windows": {"5h": {
            "used_fraction": 0.2, "resets_at": 1000, "duration_seconds": 100,
        }}}

        def boom() -> int:
            raise TimeoutError("HA slow")

        with mock.patch.object(quota, "collect_claude", return_value=claude):
            with mock.patch.object(quota, "collect_codex", return_value={"windows": {}}):
                with mock.patch.object(quota, "collect_temperature", side_effect=boom):
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
    LIMITS = [
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
            with mock.patch.dict(os.environ, {"HOME": home}):
                with mock.patch.object(
                    quota.urllib.request, "urlopen", _urlopen_returning(payload)
                ):
                    return quota.collect_claude()

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


if __name__ == "__main__":
    unittest.main()
