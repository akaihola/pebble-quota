from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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


class RefreshTests(unittest.TestCase):
    def test_refresh_collects_and_atomically_writes_snapshot(self) -> None:
        expected = {"collected_at": "1970-01-01T00:00:00Z", "services": {}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "state/latest.json"
            with mock.patch.object(quota, "collect_all", return_value=expected):
                result = quota.refresh_snapshot(output)
            self.assertEqual(result, expected)
            self.assertEqual(json.loads(output.read_text()), expected)
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
