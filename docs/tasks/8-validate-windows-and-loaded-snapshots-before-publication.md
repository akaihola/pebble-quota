---
depends-on: [7]
---

# Validate windows and loaded snapshots before publication

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

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
