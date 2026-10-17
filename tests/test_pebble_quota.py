from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from email.message import Message
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


class ClaudeBackoffTests(unittest.TestCase):
    PAYLOAD = {"five_hour": {"utilization": 20, "resets_at": 18000}}

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
            quota.urllib.request, "urlopen",
            side_effect=lambda *args, **kwargs: _FakeResponse(self.PAYLOAD)))

    def http_error(self, retry_after: str | None = None, code: int = 429) -> None:
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        self.http.side_effect = urllib.error.HTTPError(
            "https://api.anthropic.com/api/oauth/usage", code, "Too Many Requests",
            headers, None)

    def refresh(self) -> dict:
        return quota.refresh_snapshot(self.output)["services"]["claude"]

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
                          if "error" in data}, {"claude": stale["error"]})
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
        self.assertIn("offline", json.loads(self.output.read_text())["services"]["codex"]["error"])

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
            "claude": {"windows": {"5h": {"used_fraction": 0.2}}}}}
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
        self.codex.return_value = {"windows": {"5h": {"used_fraction": 0.1}}}
        self.http_error("900")
        first = self.refresh()
        self.assertNotIn("windows", first)
        self.now = 300
        self.codex.return_value = {"windows": {"5h": {"used_fraction": 0.2}}}
        self.http.reset_mock()
        self.refresh()
        self.http.assert_not_called()
        self.assertEqual(json.loads(self.output.read_text())["services"]["codex"],
                         self.codex.return_value)


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


if __name__ == "__main__":
    unittest.main()
