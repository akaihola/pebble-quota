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

## Plan

Checked on `main` at `d83a82b`. `collect_all()` keeps Claude's last good
windows after a failure with `stale: true`, `error`, `last_success_at` and
`age_seconds`. A failed Codex read drops its windows, and Codex never records
`last_success_at`. `compact_watch()` sends the pass time as `at` and drops all
of that. The phone forwards `at` and the rows. The watch colours each bar from
the received `p` but moves the marker every minute.

The steward's quota line and kandev-pacer read `latest.json`. Both treat a
service's `windows` as that pass's reading unless the service is `stale`. So
Codex keeps today's partial-failure behaviour, and the watch shows a provider
with no rows as unavailable. The only `latest.json` change is Codex recording
`last_success_at` on success. The field already exists for Claude, and the
whole-snapshot merge already writes it for Codex.

### Freshness policy

- **Bound:** a row stays fresh for 25 minutes (1,500 seconds) after its own
  reading, measured on the watch clock. A healthy cycle is at most about 21
  minutes: a 300-second wait, up to about 37 seconds of collection work (15 s
  Claude, 15 s Codex plus a 2 s exit, 5 s Home Assistant), a 900-second phone
  poll and a 15-second request timeout. One missed phone poll, or a collector
  that stopped writing, pushes rows past the bound.
- **Failure:** a row retained after a failed attempt is stale at once, however
  young its reading is. A provider with no rows is shown as unavailable.
- **Reset:** once the watch clock reaches a row's `r`, its usage belongs to an
  ended window. The bar shows no usage and no marker, whether the row is fresh
  or not.
- **Future timestamps:** a reading or pass time up to 5 minutes (300 seconds)
  ahead of the watch clock counts as age zero. Further ahead marks the row
  stale with `clock skew` and hides the temperature. The collector keeps
  timestamps as recorded and never rewrites them to "now".
- **Temperature:** it belongs to the pass in `at`, which is the pass that read
  it, including after the whole-snapshot fallback. The watch hides it when `at`
  is outside the same bound and skew. Home Assistant's two-hour entity-age
  limit stays on the host.
- **Absent values:** a row without `o` (an older API) falls back to `at`. No
  `e` means the attempt did not fail, no `n` means no provider is missing, and
  no `t` hides the temperature. `at` of 0 shows `phone sync pending` and makes
  rows that fall back to it stale.

### Wire and message changes

All additions are optional fields in protocol `v: 1`. Existing fields keep
their meaning, including `p`, which old watches still use.

- Row `o`: integral Unix seconds of the provider reading behind the row: its
  `last_success_at`, or `at` when that is missing. Retained rows keep their
  original time.
- Row `e: 1`: the provider's latest attempt failed, and the row is its last
  good reading, from `o`. It carries no error text; diagnostics stay in
  `latest.json`.
- Top-level `n`: the service codes (`C`, `X`) of providers without rows.
- Phone: sends `O<i>` (falling back to `at`), `E<i>` (0 or 1) and
  `UNAVAILABLE` (a string, possibly empty). The watch computes pace itself, so
  the unused `P<i>` keys go.

### Watch

- Move the row rules into a Pebble-free `src/c/gauges.c`: elapsed percent, row
  state, status text, gauge plan (Claude/Fable pairing, unavailable providers,
  first-row status) and temperature visibility. `watchface.c` keeps drawing,
  calendar, clock and messages.
- Fresh rows take green, yellow or red from `elapsed - used`, where `elapsed`
  is the same integer percentage that places the marker. Stale rows draw their
  used part in dark gray. Expired rows and unavailable providers draw an empty
  dark track with no marker.
- Each title row's right side shows that row's state: `stale 12m` (or `3h`,
  `2d`), `reset ?`, `clock skew` or `unavailable`. A fresh first gauge shows
  `updated Nm ago` or `phone sync pending` as before. Minute ticks redraw the
  clock and calendar, and they age the rows as well.

### Tests and checks

- Python: `o`, `e`, `n`, an unchanged old-field row shape, no error text in the
  payload, Codex `last_success_at`, and the existing expectations updated for
  the additive fields.
- End-to-end: fake providers and a fake clock drive `refresh_snapshot()`. The
  loopback `/v1/watch` response goes through the real phone script in Node
  (fake `Pebble` and `XMLHttpRequest`). The resulting message goes through the
  host-compiled watch rules. The tests skip when `node` or `cc` is missing.
  Scenarios: healthy, Claude 429, Codex failure, both failed, whole-snapshot
  fallback, recovery, old snapshot at startup, reset crossing, offline phone
  (aging and failed requests), future timestamps, missing temperature, and
  colour/marker agreement at the pace boundaries.
- Ruff, ty, the full suite, `make clean build` and Emery emulator captures
  under `xvfb-run`. The captures come from a synthetic loopback snapshot and a
  temporary bundle that points at it, never at providers.

### Docs

Update [the collector reference] and [the watchface guide] with the policy, the
new fields, old-client behaviour, the rollout order (collector API first, then
the watch bundle) and a rollback that preserves timestamps.

[the collector reference]: ../collector.md
[the watchface guide]: ../../watchface/README.md
