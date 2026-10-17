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

## Implementation and validation

- Commit `5001e41` uses `percent_fraction()` for both Claude payload formats
  and removes the unused `fraction()` heuristic. Merged locally to main.
- Two new regression tests cover 0, 1 and 100 for session, weekly_all,
  weekly_scoped, five_hour and seven_day windows. Before the fix, both tests
  failed at 1 with `1.0 != 0.01`; all cases pass after the fix.
- `python3 -m unittest discover -s tests -v`: 35 tests passed, zero failures.
- `ruff check --select E9,F63,F7,F82 collector/pebble_quota.py tests/test_pebble_quota.py`
  and `git diff --check` passed. Full Ruff has existing diagnostics, with no
  new code/message pairs: collector count fell from 10 to 9, tests stayed 14.
- No service restart, live collection, service-output write or push performed.
  The running collector retains its old code until Antti restarts it.
