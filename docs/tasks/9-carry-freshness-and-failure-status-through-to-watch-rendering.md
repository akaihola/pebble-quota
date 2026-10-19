---
depends-on: [8]
---

# Carry freshness and failure status through to watch rendering

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F3 / Step 5. 658613c already retains Claude windows with original
last_success_at, age_seconds and stale/error; compact_watch drops that metadata
and sends the current collection-pass timestamp. Codex still has no equivalent.

## Acceptance criteria

- Specify bounded freshness for 5-minute-plus-work collection and 15-minute phone
  polling. Preserve original per-provider observation times when retaining data,
  or explicitly render the provider unavailable. Reuse existing Claude metadata.
- Add only needed compatible compact/message fields, map them in JS, and show
  stale/error/unknown on watch for partial failure, old snapshots and offline phone.
  Expired windows cannot show old usage as fresh post-reset advice. Apply a stated
  policy to temperature, absent values and future timestamps.
- For fresh rows compute color and marker from the same current elapsed value;
  stale rendering overrides normal reassuring colors. Clock/calendar keep working.
- Synthetic end-to-end tests cover healthy/one/both failed, recovery, old startup,
  reset crossing, offline phone, future timestamps and missing temperature. Clear
  stale only after a valid observation. Keep sanitized detail on host, concise on watch.
- Document new semantics and additive rollout order (API before consumers), with
  old-client compatibility and timestamp-preserving rollback.
