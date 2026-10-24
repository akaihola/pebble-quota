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

## Implementation plan

1. Confirm the baseline failure and installed SDK encoding before editing.
2. Reject zero-byte string tuples in the shared string validator and add a
   regression preserving all five previous rows after a malformed update.
3. Review the focused diff, merge into main, then record all five original
   acceptance checks and the standalone reproducer at the merged commit.
4. Complete this issue without accepting it or issue [11].

## Initial findings

The reproducer on main `ca31f55` returned `accepted, accepted` and only
`Claude 5h`; its assertion failed as expected.

The installed SDK's `pypkjs.javascript.pebble.Pebble.sendAppMessage` converts
JavaScript strings to `CString`. Its `libpebble2` AppMessage serializer appends
one NUL byte to UTF-8 string data. A probe called that installed JavaScript
bridge with `UNAVAILABLE: ""`, captured the outgoing packet without a watch
connection, and serialized it: type 1, length 1, data `b'\x00'`.
The probe passed before changing the decoder. Importing the SDK initially
needed its installed C++ runtime added to the library search path.

### Initial memory report

- **Baseline reproducer:** started at once; waited 0.00 s; admission
  10835.7 MiB, final 10833.0 MiB available; starting swap 1056.9 MiB,
  swap growth 0 MiB; elapsed 0.40 s; exit 1 (expected baseline failure).
- **Initial file discovery:** an overly broad home file inventory ran before
  the memory guard was installed; no contemporaneous memory measurements
  were captured. It completed in 0.45 s with exit 0. Subsequent inventories
  were restricted to the SDK and repository.

## Implementation and review

The shared string validator now rejects zero-length tuples before accessing
string data, then requires a NUL within the declared length for every string.
The new regression sends five valid rows followed by one row with a zero-byte
`UNAVAILABLE` tuple and verifies rejection with all five earlier rows intact.
Existing empty-provider and zero-row coverage is unchanged and passes.

Reviewed the decoder and host tuple construction: `s` includes a terminator,
whereas `z` omits it. No protocol, collector, phone, or version changes.
The focused decoder suite passed all six tests; the diff has no whitespace errors.

### Premerge memory reports

- **watch-decoder-regression:** started at once; waited 0.00 s; admission 10537.3 MiB, final 10551.3 MiB available; starting swap 1056.9 MiB, swap growth 0 MiB; elapsed 0.40 s; exit 0.
- **premerge-ruff:** started at once; waited 0.00 s; admission 10610.0 MiB, final 10604.1 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 0.20 s; exit 0.

## Merged verification

Base commit: `0aac4c3abbd86a10801731fea98fc9bbc4855f62`. Delivery and tested merged commit:
`17031b0069cef67c469135f0cff48a864bf91ab1` (fast-forward merge).
All acceptance checks were recorded using `check-evidence.py record` from the
clean task checkout at that commit, before the completion commit. There is
no repository lockfile or editable Python dependency to declare; check
dependencies are empty, matching issue [11].

- **contract:** passed, 22 tests, including the new decoder regression.
- **unittest:** passed, all 100 tests in the full discovery suite.
- **ruff:** passed (`ruff check .`).
- **ty:** passed (`ty check`).
- **watch-build:** passed (`make -C watchface clean build`); no install or deployment.
- **regression:** the original standalone reproducer passed with
  `accepted, rejected` and all five previous row titles preserved.

The build emitted a format-truncation warning in the unchanged [watch renderer]
and a linker warning about an RWX load segment; it finished with exit 0.

Exact commands, tested commit, timestamps and exit codes are in the
[check receipt]. No acceptance was granted to this issue or issue [11].

### Recording memory reports

Each command below is the corresponding `check-evidence.py record` call;
commands ran sequentially, with a ten-minute timeout and process-group cleanup
on a memory or timeout stop. All finished normally.

- **record-contract:** started at once; waited 0.00 s; admission 10727.4 MiB, final 10656.9 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 8.22 s; exit 0.
- **record-unittest:** started at once; waited 0.00 s; admission 10623.4 MiB, final 10730.0 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 14.03 s; exit 0.
- **record-ruff:** started at once; waited 0.00 s; admission 10737.2 MiB, final 10703.6 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 0.20 s; exit 0.
- **record-ty:** started at once; waited 0.00 s; admission 10707.5 MiB, final 10724.7 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 0.40 s; exit 0.
- **record-watch-build:** started at once; waited 0.00 s; admission 10723.7 MiB, final 10678.6 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 1.60 s; exit 0.
- **record-regression:** started at once; waited 0.00 s; admission 10676.7 MiB, final 10656.7 MiB available; starting swap 1056.2 MiB, swap growth 0 MiB; elapsed 0.40 s; exit 0.

[check receipt]: 26-reject-zero-byte-watch-strings-before-replacing-rows.evidence.json

[watch renderer]: ../../watchface/src/c/watchface.c
