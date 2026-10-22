Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D3 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Extract only the whole-snapshot fallback merge into a pure function with no disk, provider or clock access and no mutation of its inputs. `refresh_snapshot` keeps checkpoints, publication, the in-memory update before writes and the existing unavailable exception. Claude's per-provider retention and its timestamps are unchanged. If the open freshness proposal already supplies this seam, merge into it instead.

## Acceptance

- Pure cases keep the old quota, collection time and temperature, merge new attempts, cooldown and errors, and compute the same stale ages; an empty prior state stays unavailable; inputs stay unchanged.
- Integration tests, plus a retained-temperature case, tell apart both-failed with prior Claude from both-failed with only prior Codex, a first 429 without rows, restart interval suppression, and a write failure with new in-memory cooldown.
- Full offline checks pass; persisted schema and compact payloads are unchanged for those sequences. This does not complete the freshness proposal.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

## Plan

1. Pin current behaviour first: exact persisted snapshots and compact payloads
   for both providers failing over prior Claude rows versus prior Codex rows,
   with a retained temperature, and the persisted state of a first 429 without
   rows. Add direct data cases for the merge function, which must fail until it
   exists.
2. Extract the loop in `refresh_snapshot`'s unavailable branch into one pure
   function in the collector module that copies the previous snapshot, merges
   attempted service fields and computes stale ages from the attempted
   collection time. `refresh_snapshot` keeps checkpoints, the `retained` check,
   the in-memory update before the write, the write and the exception.
3. Compare old and new code on the integration sequences (both-failed cases,
   first 429, restart suppression, write failures) for identical written
   snapshots and compact payloads; run focused tests, then the full offline
   unittest, Ruff and ty checks under the memory guard; update the collector
   guide; review, commit and merge into main.

[The freshness proposal] is still an unverified proposal with no
implementation, so it supplies no seam to merge into. The review's F3 location
was rechecked on main at `54c414a`: the fallback is now at lines 594–610 of
the collector.

## Outcome and verification

[The collector] now has `merge_unavailable_snapshot(previous, attempted)`. It
deep-copies the previous normalized snapshot, applies the attempted services'
fields over it, and marks services that still have windows stale, with their
age at the attempted collection time. It reads no disk, provider or clock and
does not modify its inputs. `refresh_snapshot` calls it in the unavailable
branch and still owns the attempt checkpoints, the `retained` check, the
in-memory update of `previous` before the write, the write and the
unavailable exception. Claude's per-provider retention in `collect_all` is
untouched. [The collector guide] names the function in its fallback paragraph.

[The tests] gained:

- `UnavailableMergeTests`: direct data cases for keeping the old windows,
  `collected_at` and temperature while new attempt, cooldown and error fields
  replace old ones and the new temperature error is dropped; stale ages from
  `last_success_at`, from the old `collected_at`, clamped at zero, and the
  no-timestamp case that marks rows stale without an age; an empty prior state
  that stays unavailable (compact `at: null`, no rows). Inputs are compared with
  deep copies afterwards.
- `test_both_failed_publishes_retained_claude_but_keeps_whole_codex_snapshot`:
  exact persisted snapshot and compact payload when both providers fail. With
  prior Claude rows the pass publishes, with the new `collected_at` and the new
  temperature; with only prior Codex rows it raises "preserving previous" and
  keeps the old `collected_at` and old temperature (the retained-temperature
  case).
- The first-429-without-rows test now pins the exact persisted
  scheduling-only state.

Existing integration tests still cover restart interval suppression and write
failures that keep the new cooldown in memory.

The direct cases failed before extraction because the function did not exist;
both integration pins passed on the old code first. After extraction, all 25
focused refresh, backoff, startup, validation and merge tests and all 74 offline
tests passed. `ruff check .`, `ty check` and `git diff --check` passed.

A throwaway differential script, not committed, loaded the old and new
collector and ran eight sequences through each: both failed over prior Claude
rows, over prior Codex rows, the first 429 without rows and its later retry,
restart suppression after success and after total failure, `serve`-style
in-memory state across three failing writes, an atomic-replace failure over a
good file, and an invalid Codex refresh over prior Codex rows. It recorded
every written snapshot, every in-memory state, every exception and the final
compact payload. All eight were identical between the two versions, so the
persisted schema and compact payloads did not change for these sequences. Its
first run mocked the 429 so that it returned the error instead of raising it.
After fixing that mock, the rerun above exercised the cooldown paths. No
provider, credential, network or installed CLI was used.

This does not complete [the freshness proposal]. No acceptance gaps remain.
Completion is pending acceptance; the acceptance checkbox remains unchecked.

### Observation for the steward

The differential run showed existing behaviour, unchanged here, that belongs
to [the freshness proposal]. After a whole-snapshot fallback over Codex rows,
the next pass in which both providers are interval-suppressed copies the stale
Codex service back into `collect_all`'s output. The snapshot is then usable, so
it publishes with a new `collected_at` and the new temperature, while the
Codex `age_seconds` stays at the value from the fallback pass.

## Guarded command resource record

Each command ran alone under a wrapper with a 300-second limit and memory
checks every 0.1 seconds. Admission required 2048 MiB available, with the
specified 10-minute wait and 1536 MiB fallback; running limits were 1024 MiB
available and 512 MiB swap growth. Waits are in seconds and memory readings in
MiB. The first command is the expected run before extraction.

- `python3 -m unittest discover -s tests -p test_pebble_quota.py -k UnavailableMergeTests -k test_both_failed_publishes -k test_first_429_without_rows`: **started at once**; wait 0.0; admission 2673, final 2664; starting swap 2620, swap growth 0; elapsed 0.30 seconds; exit 1.
- `python3 -m unittest discover -s tests -p test_pebble_quota.py -k test_both_failed_publishes -k test_first_429_without_rows -v` (old code): **started at once**; wait 0.0; admission 2734, final 2727; starting swap 2620, swap growth 0; elapsed 0.52 seconds; exit 0.
- `python3 -m unittest discover -s tests -p test_pebble_quota.py -k UnavailableMergeTests -k RefreshTests -k ClaudeBackoffTests -k StartupTests -k ValidationTests`: **started at once**; wait 0.0; admission 2727, final 2708; starting swap 2598, swap growth 0; elapsed 1.14 seconds; exit 0.
- Differential script, first run with the faulty 429 mock: **started at once**; wait 0.0; admission 2587, final 2539; starting swap 2493, swap growth 0; elapsed 1.08 seconds; exit 0.
- Differential script, after the mock fix: **started at once**; wait 0.0; admission 2571, final 2560; starting swap 2478, swap growth 0; elapsed 1.24 seconds; exit 0.
- `python3 -m unittest discover -s tests -v`: **started at once**; wait 0.0; admission 2480, final 2593; starting swap 2481, swap growth 22; elapsed 11.21 seconds; exit 0.
- `ruff check .`: **started at once**; wait 0.0; admission 2709, final 2705; starting swap 2515, swap growth 0; elapsed 0.04 seconds; exit 0.
- `ty check`: **started at once**; wait 0.0; admission 2739, final 2630; starting swap 2528, swap growth 4; elapsed 0.91 seconds; exit 0.

[The freshness proposal]: 9-carry-freshness-and-failure-status-through-to-watch-rendering.md
[The collector]: ../../collector/pebble_quota.py
[The collector guide]: ../collector.md
[The tests]: ../../tests/test_pebble_quota.py
