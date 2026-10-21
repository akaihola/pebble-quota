# Validate windows and loaded snapshots before publication

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Promoted by the steward, 2026-10-22 01:58 refill (D13). Goal: agentic-leverage (pebble-quota is tier 1 on the goals page). The dependency on [7] is dropped: these criteria need only the local unittest suite, not the CI gate, which stays with [7]. Checked on current `main` before promoting: `has_quota_data()` in `collector/pebble_quota.py` still tests `service.get("windows")` for truthiness. Estimated 2 h.

Constraints for this run: tests use fakes and fixtures only; never call an authenticated provider, print a credential, or restart the collector service (the steward restarts it after acceptance, D78). Memory: before each command, wait up to 10 minutes for `MemAvailable` of at least 2 GiB; if it doesn't come, start anyway at 1.5 GiB or more. Stop a running command when `MemAvailable` falls below 1 GiB or swap grows by more than 512 MiB. Run `python3 -m unittest discover -s tests -v` before merging. Handoff: a short outcome and the test result; put detail in this task record.

Review F2 / Step 4. has_quota_data still tests dictionary truthiness and
compact_watch can fail on one bad window. 658613c also reads prior JSON before
collecting: a nonempty array root now prevents provider attempts.

## Acceptance criteria

- One small normalized validation boundary checks container shapes, finite usage
  with explicit out-of-range policy, reset timestamps, bounded positive durations,
  scopes and watch-representable values; reject bad windows individually.
- Valid windows from either provider survive other malformed windows. Only usable
  rows constitute successful quota publication; all-invalid refresh preserves the
  last good quota data. Preserve atomic replacement.
- Load old snapshots as untrusted input. Missing/corrupt/wrong-root/nested-state
  shapes cannot block an otherwise healthy collection; no guessed data repair.
- Preserve Claude cooldown across restart/first 429 even when no usable rows exist;
  define unavailable-data behavior without presenting cooldown-only state as a
  successful quota reading. Test this together with 658613c retention behavior.
- Test NaN/infinity, numeric strings, bad timestamps, missing fields, malformed
  scope/container, zero/negative duration, startup without state, disk-write failure,
  partial/total provider failure and invalid refresh over good state. Replace the
  current successful-refresh fixture containing only {"used": 1} with valid windows.
- Document validation/unavailable-data semantics; HTTP gracefully handles damaged
  state and returns sanitized diagnostics rather than raw exception text.

## Implementation plan

1. Normalize provider windows and loaded snapshots through one validation boundary;
   reject individual invalid rows and retain only safe scheduling metadata.
2. Keep attempt/cooldown persistence separate from quota availability. Preserve
   valid prior quota on an unusable refresh, including write-failure memory state.
3. Return HTTP 503 for unavailable quota and fixed diagnostic messages for failures.
4. Add fixture-only regression coverage, run the full unittest suite under the
   memory guard, review the diff, rebase and merge, then mark complete unaccepted.


## Outcome and verification

Implemented on 2026-10-22. The shared normalization boundary rejects malformed
windows independently, validates provider percentages and timezone-aware resets,
and bounds values for the signed 32-bit watch transport and arithmetic. Invalid
usage is rejected rather than clamped. Fable is the supported Claude model scope;
unscoped windows cannot carry a scope. Invalid duplicate provider windows cannot
erase valid earlier entries.

Snapshot loading discards invalid shapes and scheduling fields. Healthy collection
continues after missing, corrupt, array-root or nested malformed state. Only usable
windows qualify as quota data. A rowless refresh retains prior valid quota while
saving attempts and Claude cooldown; a first 429 without rows remains unavailable
and survives restart. Existing Claude stale-window retention continues working.
Failed atomic replacement leaves the disk snapshot intact and preserves the new
cooldown in memory. Persistent write failure still prevents restart persistence.
The HTTP endpoint serves surviving valid rows or a fixed 503 response. Snapshot
and log diagnostics use fixed categories, without raw exception messages.

Validation: `python3 -m unittest discover -s tests -v` passed all 57 tests. Tests
use temporary credentials, fake provider responses/processes, and loopback HTTP;
the suite guards against real credentials, external network and live processes.
Coverage includes malformed scopes/containers, missing fields, numeric strings,
booleans, nonfinite and out-of-range numbers, invalid timestamps and durations,
startup without state, partial/total failure, malformed refresh over valid state,
first-429 cooldown across restart and interval retention, atomic write failure,
and sanitized HTTP errors. `git diff --check` passed. Inline diff review checked
publication, scheduling and watch representation paths. No provider calls or
collector-service restarts were performed. No remaining implementation gaps.

Earlier local suite runs exposed fractional ISO collection timestamp handling,
changed fixed diagnostics and the retained-row interval behavior; these were
resolved before the final passing run. The 56-test run passed before the final
scope and retained-state regressions increased the suite to 57 tests.

Implementation and semantics: [collector], [fixture suite], [collector documentation].

[collector]: ../../collector/pebble_quota.py
[fixture suite]: ../../tests/test_pebble_quota.py
[collector documentation]: ../../README.md#collector

## Memory-guarded commands

Each row records `python3 -m unittest discover -s tests -v`, run alone under a
600-second timeout with process-group termination on low memory or swap growth.
Readings are MiB. No command was stopped, used fallback admission, or remained
short after ten minutes. Negative swap growth means swap use fell.

| Run | Outcome | Wait (s) | Admission | Final | Starting swap | Swap growth | Elapsed (s) | Exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | started at once | 0.0 | 2309 | 2291 | 2501 | -4 | 2.92 | 1 |
| 2 | started at once | 0.0 | 2645 | 2652 | 2449 | 0 | 3.63 | 1 |
| 3 | started at once | 0.0 | 2542 | 2531 | 2443 | 0 | 3.93 | 0 |
| 4 | started at once | 0.0 | 2771 | 2803 | 2427 | 0 | 11.28 | 0 |

## Merge and handoff

The canonical tracker start move was committed immediately on main as `34963ac`;
the plan was committed there as `e14b2eb`. Implementation `44a038f` was rebased
on main and merged with `git merge --ff-only` after the final 57-test pass.
Completion move `375f985` places this issue in Completed / Accepted with `[ ]`;
acceptance remains with the steward. The branch and worktree are retained.
The steward restarts the collector after acceptance under D78; this run made no
service change. No owner action is required and this thread can be closed.
