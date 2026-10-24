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

## Steward notes, 2026-10-24

Promoted from Unverified proposals by the steward (tier 1: the quota source);
this authorizes the implementation, not a deployment. Confirmed on `main`
(`b1ef6a8`): `compact_watch()` sends the pass's `collected_at` as `at` for
every row and drops `stale`, `age_seconds` and `last_success_at`, so a Claude
window kept after a 429 reaches the watch as fresh.

- Keep `latest.json` backward compatible: add fields, never rename or remove
  one or change its meaning. kandev-pacer and the steward's quota line read it.
- `pebble-quota.service` runs `collector/pebble_quota.py` from this checkout.
  Don't restart it; the steward restarts it after acceptance. Installing on
  the phone or watch is Antti's. Check the watch side on the Emery emulator
  under `xvfb-run` (`watchface/shell.nix`, the installed SDK) and record what
  each capture shows, or record the missing prerequisite. Never claim
  on-device verification.
- Keep machine paths out of committed docs and code; the check receipt is
  exempt. A formatting-only change that a required check demands is allowed.
- Size: about 3–4 hours.
