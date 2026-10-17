# Fix Claude 1% showing as 100%

Steward issue, 2026-10-17. The same defect as [1], on the Claude side.

## Problem

`fraction()` in `collector/pebble_quota.py` treats any value at or below 1 as a
fraction already. Claude's usage endpoint reports percentages: the
`limits[].percent` field and the legacy `five_hour` and `seven_day`
`utilization` fields. So 1% becomes `used_fraction` 1.0, which the watch face
shows as 100%.

Seen on 2026-10-17: the reading collected at 19:56:36 UTC gave Claude's 5-hour
window `used_fraction` 1.0, just after the window opened at about 19:40 UTC.
The next reading, at 20:01:37 UTC, gave 0.02. The steward's `quota.jsonl`
recorded the wrong value.

## Plan

1. Convert Claude's `percent` and `utilization` from percent to fraction
   unconditionally, as `percent_fraction()` does for Codex.
2. Remove `fraction()` if nothing else uses it.
3. Add regression tests for 0, 1 and 100 on both Claude paths (`limits[]` and
   the legacy pair), including all supported limits kinds.
4. Run the regression tests before and after the fix, then the full unittest
   suite and focused lint checks. Review and merge locally to main, and mark
   complete pending acceptance without restarting the service or pushing.

## Acceptance criteria

- Claude values of 0, 1 and 100 produce `used_fraction` 0.0, 0.01 and 1.0 on
  both paths, with regression coverage.
- `python3 -m unittest discover -s tests -v` passes from the repository root.

## Ground rules

- Don't restart `pebble-quota.service`: the running collector keeps the old
  code until Antti restarts it. A live check is optional, as one collection
  written to `$TMPDIR`, never to the service's output file.
- Don't push.
