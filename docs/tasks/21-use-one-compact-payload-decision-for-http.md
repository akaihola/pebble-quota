Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D1 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Compute `compact_watch` once in the watch route, validate its `q` and `at`, then serialize that object. Remove checks inside the compactor that its own normalization already guarantees. Keep the raw-input boundary, row order and truncation, timestamp and rounding rules, diagnostic categories, auth handling and public helper behaviour.

## Acceptance

- Authenticated loopback fixtures keep valid and mixed-valid payloads, accept timestamp zero, and return a fixed 503 for missing, corrupt, wrong-root, rowless and invalid-timestamp snapshots.
- Every serialized row is asserted valid, and valid siblings survive.
- Existing 401, 404 and config tests and all offline checks pass; the route no longer runs two independent normalization and publication paths.
- No live quota request, phone or watch is needed.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

## Plan

1. Pin authenticated loopback publication behavior before editing production:
   valid/mixed rows, zero and invalid timestamps, missing/corrupt/wrong-root
   and rowless snapshots, fixed 503 body and sanitized diagnostic categories.
   Assert the complete serialized rows, ordering and truncation.
2. Compute one compact payload in the HTTP route, validate its rows and
   timestamp, and serialize it. Use normalized window fields directly inside
   the compactor; preserve public raw-input normalization and helper behavior.
3. Run focused HTTP/validation checks, the offline Python suite, Ruff, ty and
   JavaScript syntax checks sequentially under the memory guard. Review the
   diff, record results here, merge onto main and complete the tracker entry
   with acceptance unchecked.

The review's F1/D1 references were rechecked on current main: the duplicate
publication path remains at collector lines 689–693 and redundant compactor
checks at lines 534–538. No policy change is needed.

## Outcome and verification

The [collector] now builds one compact payload, checks nonempty `q` and
non-`None` `at` (including zero), and serializes that same object. The public
compactor still normalizes raw input; normalized window fields and temperature
are used directly. `has_quota_data` remains unchanged for its other callers.
Read-error handling, diagnostic categories, auth, row selection and rounding
remain unchanged.

The expanded authenticated loopback test in [the offline suite] pins the full
payload for valid and mixed-valid snapshots: all five emitted rows, Claude /
Fable / Codex order, sixth-row truncation, banker rounding, pace, temperature,
zero/integer timestamps and timezone-aware fractional timestamp truncation.
Missing files, corrupt JSON, wrong roots, rowless snapshots and missing/invalid
timestamps produce identical fixed 503 bodies with the existing sanitized logs.
Existing public-helper invalid-row tests retain valid siblings for both providers.

Tests were written and run before the production edit. The first pinning run
failed because the new test expected `FileNotFoundError`; the existing diagnostic
allowlist maps that exception to `Quota unavailable`. The expectation was
corrected without changing production behavior; all 10 validation tests then
passed on the original implementation. After the edit, the focused HTTP filter
passed (2 tests), then all 66 offline tests passed with no skips, including
401/404/config and live-access guard checks. Ruff initially reported nested
contexts in the new fixture; these were combined. Ty initially inferred too
narrow a fixture dictionary; it now has an explicit `dict[str, Any]` annotation.
Both static checks subsequently passed. JavaScript syntax passed. After those
test-only edits the HTTP fixture passed again (1 test). Diff whitespace checks
passed, and review confirms one route compaction/normalization path with no
trusted-input bypass or fetch added.

No live quota request, device, browser suite, PBW build, service change or
provider compatibility probe was needed or performed. No acceptance conditions
remain unresolved; user/steward acceptance stays unchecked.

## Memory-guarded commands

Commands ran sequentially with a 300-second timeout, process-group cleanup and
0.1-second memory sampling. Admission waits up to 600 seconds for 2,048 MiB,
permits fallback only at 1,536 MiB, and stops below 1,024 MiB or above 512 MiB
swap growth. Measurements below are MiB; elapsed excludes admission wait.
No fallback, timeout or running stop occurred. Command output is excluded.

- **Run 1 — `python3 -m unittest discover -s tests -p test_pebble_quota.py -k ValidationTests -v`:** started at once; wait 0.00 s; admission MemAvailable 2445.44; final 2327.10; starting swap 2495.00; swap growth 0.00; elapsed 3.40 s; exit 1.
- **Run 2 — `python3 -m unittest discover -s tests -p test_pebble_quota.py -k ValidationTests -v`:** started at once; wait 0.07 s; admission MemAvailable 2464.97; final 2412.32; starting swap 2494.98; swap growth 0.00; elapsed 3.12 s; exit 0.
- **Run 3 — `python3 -m unittest discover -s tests -p test_pebble_quota.py -k http -v`:** started at once; wait 0.00 s; admission MemAvailable 2360.07; final 2345.29; starting swap 2490.73; swap growth 0.00; elapsed 2.21 s; exit 0.
- **Run 4 — `python3 -m unittest discover -s tests -v`:** started at once; wait 0.00 s; admission MemAvailable 2374.21; final 2221.14; starting swap 2490.48; swap growth 8.50; elapsed 17.79 s; exit 0.
- **Run 5 — `ruff check .`:** started at once; wait 0.00 s; admission MemAvailable 2340.96; final 2328.81; starting swap 2494.48; swap growth 0.00; elapsed 0.31 s; exit 1.
- **Run 6 — `ruff check .`:** started at once; wait 0.00 s; admission MemAvailable 2363.61; final 2363.67; starting swap 2493.98; swap growth 0.00; elapsed 0.20 s; exit 0.
- **Run 7 — `ty check`:** started at once; wait 0.00 s; admission MemAvailable 2375.71; final 2357.90; starting swap 2489.98; swap growth 0.00; elapsed 3.21 s; exit 1.
- **Run 8 — `ty check`:** started at once; wait 0.07 s; admission MemAvailable 2375.87; final 2349.05; starting swap 2479.71; swap growth 0.00; elapsed 2.62 s; exit 0.
- **Run 9 — `node --check watchface/src/pkjs/index.js`:** started at once; wait 0.00 s; admission MemAvailable 2358.47; final 2361.30; starting swap 2479.71; swap growth 0.00; elapsed 0.30 s; exit 0.
- **Run 10 — `python3 -m unittest discover -s tests -k http_damaged -v`:** started at once; wait 0.00 s; admission MemAvailable 2362.09; final 2348.16; starting swap 2479.46; swap growth 0.00; elapsed 2.19 s; exit 0.

- **Run 11 — `ruff check .`:** started at once; wait 0.00 s; admission MemAvailable 2379.51; final 2377.40; starting swap 2478.46; swap growth 0.00; elapsed 0.10 s; exit 0.

[collector]: ../../collector/pebble_quota.py
[the offline suite]: ../../tests/test_pebble_quota.py

## Merge and handoff

The start move was committed on canonical main as `7f07d1b`, immediately
followed by plan commit `cbb24a8`; the feature branch was rebased onto that plan.
Implementation, pinning tests and this record are merged into main before the
completion move. The retained feature branch and worktree remain available.
No push, PR or deployment is part of this issue. No owner action is needed;
there are no agent-owned follow-ups or outstanding acceptance conditions.

Implementation commit `96e0f85` was merged with `git merge --ff-only`.
Completion commit `264f602` moved the issue to Completed / Accepted. A fresh
Hai read confirms that state and `accepted: false`; the canonical tracker has
no uncommitted changes. Final task-link, private-path and whitespace checks
passed. This record includes the initial failed checks and their passing
reruns; none remains unresolved.
