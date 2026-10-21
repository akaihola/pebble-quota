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
