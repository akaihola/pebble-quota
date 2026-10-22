Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D2 of [the 2026-10-22 architecture review], filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Extract the rate-limit result parsing into one pure provider-specific function in `collector/pebble_quota.py`. Move value-only cases to direct calls; keep integration coverage of the handshake, notifications, deadline, environment and teardown. Keep the wrapped and direct formats, duration-based labels, sibling salvage and all diagnostic text.

## Acceptance

- Direct cases cover 0, 0.5, 1, 2, 100 and missing usage, bounded durations, a malformed primary with a valid secondary, an invalid result and legitimate no-window results; duplicate-duration behaviour and window order are unchanged.
- Fake-child tests still prove EOF, timeout and RPC errors, forced kill, reaping and closed pipes; a 1 % adapter result still compacts to `u: 1`.
- Full offline checks pass without invoking the installed Codex CLI or making a live quota request.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker].

## Plan

1. Pin result decoding with direct dictionary cases for formats, percentages,
   duration bounds, sibling salvage, ordering, duplicates and diagnostics.
2. Extract one pure Codex decoder; retain handshake, deadline and teardown
   coverage with fake children, including compact 1 % output.
3. Run the focused tests and full offline unittest, Ruff and ty checks under
   the memory guard; review, commit and merge into main.

Current main still contains the F2 decoding block inside `collect_codex`;
the review's proposed extraction applies without a behavior change.

## Outcome and verification

Extracted `codex_service_from_result` in [the collector]. The transport calls
it after the rate-limit reply. Wrapped/direct formats, duration labels,
primary-before-secondary ordering, secondary replacement of a duplicate
label, sibling salvage and fixed diagnostics retain their existing behavior.
The two-stage handshake, shared deadline, environment and teardown are unchanged.
The review's F2 location was rechecked on main at `052de11` before extraction.

[The tests] now call the decoder directly for percentages 0, 0.5, 1, 2 and
100, missing usage, duration bounds, invalid results, empty windows, ordering,
duplicates and malformed-primary salvage. Generated fake children retain
transport and cleanup coverage, and the success path compacts 1 % to `u: 1`.

The new direct tests failed before extraction because the decoder did not
exist. After extraction, all 14 focused Codex tests and all 70 offline tests
passed. `ruff check .`, `ty check` and `git diff --check` passed. Tests blocked
real provider access; neither the installed CLI nor a live quota request was
used. Installed CLI compatibility remains outside this task's scope.

Reviewed the final diff: no transport redesign or diagnostic changes, and no
new dependency. No acceptance gaps or agent follow-ups remain. Completion
is pending acceptance; the acceptance checkbox remains unchecked.

## Guarded command resource record

Each command ran alone with a 300-second limit and memory monitoring every
0.1 seconds. Admission required 2048 MiB available, with the specified
10-minute wait and 1536 MiB fallback; running limits were 1024 MiB available
and 512 MiB swap growth. All waits below are in seconds; all memory readings
are MiB. The initial failing check is the expected pre-extraction test run.

- `python3 -m unittest discover -s tests -p test_pebble_quota.py -k CodexResultTests`: **started at once**; wait 0.0; admission 2886, final 2883; starting swap 2476, swap growth 0; elapsed 0.3 seconds; exit 1.
- `python3 -m unittest discover -s tests -p test_pebble_quota.py -k Codex`: **started at once**; wait 0.0; admission 2739, final 2816; starting swap 2473, swap growth 6; elapsed 6.38 seconds; exit 0.
- `python3 -m unittest discover -s tests -v`: **started at once**; wait 0.0; admission 2696, final 2692; starting swap 2481, swap growth 0; elapsed 10.1 seconds; exit 0.
- `ruff check .`: **started at once**; wait 0.0; admission 2646, final 2654; starting swap 2480, swap growth 0; elapsed 0.2 seconds; exit 0.
- `ty check`: **started at once**; wait 0.0; admission 2693, final 2708; starting swap 2480, swap growth 0; elapsed 2.01 seconds; exit 0.

[the 2026-10-22 architecture review]: ../reviews/2026-10-22-architecture-review.md#draft-issues
[the pebble-quota tracker]: ../../TASKS.md
[the collector]: ../../collector/pebble_quota.py
[the tests]: ../../tests/test_pebble_quota.py
