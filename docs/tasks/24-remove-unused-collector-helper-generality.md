Steward issue, 2026-10-22 08:00 digest (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 45 min.

This is draft D5 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there now that its prerequisite D1 ([21]) is done; read that draft and the finding it cites (F5) before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Make the HTTP handler a directly named class and update repository call sites. Narrow `iso_from_epoch` to numeric epoch formatting and remove its unused `None` and string branches. Keep its name, fractional-second support, datetime formatting and range-error behaviour. Don't change the snapshot reader's accepted ISO timestamps or the typed server attributes.

## Acceptance

- A caller search confirms the removed inputs and the factory customization are unused in this repository.
- Existing cooldown, HTTP, corrupt-snapshot, out-of-range Retry-After and fractional HA-age tests pass; Ruff and ty stay clean.
- A small numeric formatting assertion preserves zero and fractional epochs.
- No change to routes, headers, disk format or emitted JSON. No live quota request, phone or watch is needed.

## Ground rules

- Behaviour stays the same unless the acceptance above says otherwise. Write the pinning test first.
- Run at most one focused test command at a time, under your launch prompt's memory rule.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

## Plan

1. Recheck the review's F5 locations on `main` at `63ee40e` and search every
   caller of `iso_from_epoch` and `make_handler` in the repository.
2. Pin numeric formatting first: zero and a fractional epoch, passing on the
   old code.
3. Narrow `iso_from_epoch` to `float -> str`, keeping `datetime.fromtimestamp`
   and its range errors. Move the handler class to module level as `Handler`
   and pass it directly to `QuotaServer` in `main` and the tests.
4. Run Ruff, ty and the offline unittest suite under the memory guard; review,
   commit and merge into main.

## Outcome and verification

The F5 locations moved since the review's commit. On `main` at `63ee40e`,
`iso_from_epoch` was at lines 57–62 of [the collector], with production calls
at lines 465 (`claude_retry_delay`'s range check, `now + delay`) and 509
(`retry_at`, an epoch plus a delay). `make_handler` was at lines 681–724, called
with no arguments at line 745 and at five places in [the tests].

Caller search (`git grep` over the whole tree): every `iso_from_epoch` call
passes a number. Production passes the two sums above; the tests pass integer
literals, `self.NOW - age` with fractional ages, and loop variables that are
integers (one loop skips its `None` case before calling). No call passes `None`
or a string. The [historical spike] has its own copy of the old function and
does not import the collector, so it is unaffected. `make_handler` took no
arguments and captured nothing; its class read its configuration from
`self.server`. Nothing subclassed, patched or customized the returned class.
Two historical records ([the September review] and the [checker-fixes record])
name `make_handler`. They describe the code as it was, so they stay as written.

[The collector] now has:

- `iso_from_epoch(value: float) -> str`, which returns
  `datetime.fromtimestamp(value, timezone.utc)` in ISO form with `Z`. The `None`
  and string branches and the `float()` conversion are gone. Integers and
  fractional seconds format as before. Out-of-range values still raise
  `OverflowError`, `ValueError` or `OSError`, which `claude_retry_delay` relies
  on.
- `class Handler(BaseHTTPRequestHandler)` at module level, with the typed
  `server: QuotaServer` attribute. Apart from indentation, its body is
  unchanged (`git diff -w` shows only the removed `def` and `return` lines).
  `main` and the five test servers pass `Handler` to `QuotaServer`.

`epoch`, the snapshot reader's timestamp parser, and `QuotaServer` are
unchanged. Routes, headers, the disk format and the emitted JSON do not change.

[The tests] gained `IsoFromEpochTests.test_formats_zero_and_fractional_epochs`:
`0` formats as `1970-01-01T00:00:00Z` and `1.5` as
`1970-01-01T00:00:01.500000Z`. It passed on the old code before the change.

Verification on the branch after rebasing on `63ee40e`:

- `ruff check .` (0.16.8) and `ty check` exit 0.
- `python3 -m unittest discover -s tests -v`: all 75 tests pass, 74 existing and
  the new one. They include the cooldown tests
  (`test_429_keeps_windows_and_persists_cooldown_until_recovery`,
  `test_write_failure_keeps_429_in_memory_and_waits_between_attempts` and the
  restart and atomic-replace cooldown tests), the HTTP tests
  (`test_config_page_served_without_auth`,
  `test_503_does_not_reflect_exception_in_response`,
  `test_http_damaged_state_and_diagnostics_are_sanitized`), the
  corrupt-snapshot test `test_damaged_disk_state_cannot_block_healthy_collection`,
  the out-of-range Retry-After test
  `test_unhelpful_retry_after_uses_exponential_backoff_with_cap` (header
  `"9" * 100`) and the fractional HA-age test
  `test_entity_age_boundaries_and_timezone_offsets` (ages 7200.001 and -0.001).
  The suite uses temporary loopback servers and blocks real provider access.

No live quota request, phone or watch was used. No acceptance gaps remain.
Completion is pending acceptance; the acceptance checkbox remains unchecked.

## Guarded command resource record

The full suite ran alone under a wrapper with a 300-second limit and memory
checks every second. Admission required 2048 MiB available, with the specified
10-minute wait and 1536 MiB fallback; running limits were 1024 MiB available
and 512 MiB swap growth. Memory readings are in MiB. Ruff, ty and the single
pinning test ran unguarded because each finishes in about a second.

- `python3 -m unittest discover -s tests -v`: **started at once**; wait 0
  seconds; admission 2534, final 2333; starting swap 2082, swap growth −1;
  elapsed 19 seconds; exit 0.

[The collector]: ../../collector/pebble_quota.py
[The tests]: ../../tests/test_pebble_quota.py
[historical spike]: ../../spikes/001-quota-collectors/
[the September review]: ../2026-09-19-architecture-review-and-remediation-plan.md
[checker-fixes record]: 19-fix-the-seven-ruff-and-four-ty-findings-and-document-both-checks.md
