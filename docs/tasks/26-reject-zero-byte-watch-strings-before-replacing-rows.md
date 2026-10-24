Steward issue, 2026-10-24 11:00 tick (steward decisions D43 and D95). Goal: agentic-leverage, tier 1 (the quota source). Estimated 45 min.

## Why

The steward's independent spot check of [11] on `main` `364d20d` reran all five of its receipt checks with passing results, but found one gap against [11]'s second acceptance criterion ("Validate C tuple type/length and coherently replace rows"). In `watchface/src/c/gauges.c`, `field_string()` starts with `length = 0` and looks for a NUL only when `field->length > 0`. `UNAVAILABLE` allows zero characters, so a zero-byte string tuple, which has no terminator, passes and replaces the displayed rows. A valid empty C string is one byte long.

The existing host harness reproduces it: send a valid five-row message, then a one-row message with `UNAVAILABLE=("z", "")`. Observed `accepted, accepted`, leaving only the `Claude 5h` row; required `accepted, rejected`, keeping all five rows. The reproducer, run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from tests.test_pebble_quota import WatchDecodeTests

WatchDecodeTests.setUpClass()
try:
    case = WatchDecodeTests()
    before = case.message(case.FIVE, R2=("i4", case.WEEK + 1))
    malformed = case.message(case.FIVE[:1], UNAVAILABLE=("z", ""))
    actual = case.titles(before, malformed)
    print(actual)
    assert actual == (["accepted", "rejected"], case.UNPAIRED)
finally:
    WatchDecodeTests.doClassCleanups()
PY
```

[11] stays completed but unaccepted until this is fixed.

## What to do

1. Run the reproducer on `main` and confirm it fails as above.
2. Before changing the decoder, confirm from the installed Pebble SDK's phone-to-watch encoding (or an emulator message) that an empty JavaScript string arrives as a one-byte tuple holding only the NUL. A healthy update with no unavailable services must still be accepted. If an empty string arrives as zero bytes, stop and record the evidence in this task record; don't change the phone protocol here.
3. Require a NUL within every `FIELD_STRING` tuple, `UNAVAILABLE` included, so a zero-length tuple is rejected, while a one-byte terminated empty string stays valid.
4. Add the reproducer to `WatchDecodeTests` as a regression that proves the malformed second message is rejected and all five earlier rows remain. Keep the existing valid empty-provider and zero-row cases.

## Constraints

- No protocol, version, collector or phone change; no service restart, install or deployment.
- Keep private paths and host names out of committed docs and code; the check receipt is exempt.
- Follow your launch prompt's memory rule; one heavy command at a time.

## Acceptance

- The reproducer passes on the merged commit.
- [11]'s five receipt checks pass at the merged commit, recorded with `check-evidence.py record` under the same check IDs, plus the new regression: `contract`, `unittest`, `ruff`, `ty`, `watch-build` (commands as in [11]'s `.evidence.json`).
- Handoff: a short outcome; details go in this task record. The steward judges [11] together with this issue afterwards; don't accept either here.

Tracker: [the pebble-quota tracker](../../TASKS.md).

[11]: 11-enforce-the-five-row-collector-phone-and-watch-contract.md
