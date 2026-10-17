# Back off on HTTP 429 from Claude's usage endpoint and keep the last reading

Filed by the steward (`agents/steward/` in the vault) on 2026-10-17. Goal:
agentic-leverage, tier 1. pebble-quota is the quota source for the watch face
and for the steward's `quota.jsonl`.

## Evidence

- `collect_claude()` in `collector/pebble_quota.py` calls
  `https://api.anthropic.com/api/oauth/usage` on every refresh (every 5 minutes)
  with no retry or backoff.
- `latest.json` carried `HTTPError: HTTP Error 429: Too Many Requests` for Claude
  instead of windows on 2026-10-16 at 16:37 UTC, and without a break from about
  02:00 to 07:00 UTC on 2026-10-17. Codex was unaffected.
- kandev-pacer polls the same endpoint with the same OAuth credentials
  (`USAGE_URL` in `kandev_pacer/provider.py`). Its fetch also got 429 at 02:00
  UTC but recovered within minutes, so the two clients may share one limit.

## Work

1. Find out what the limit is keyed on and whether 429 responses carry
   `Retry-After` or rate-limit headers. Compare with how kandev-pacer's
   provider caches and backs off.
2. After a 429, wait for `Retry-After`, or back off exponentially, before the
   next Claude request instead of retrying on every refresh.
3. Keep the last good Claude windows in `latest.json`, marked with their age and
   the error, so readers can tell a stale reading from none. Keep existing
   readers working: the watch face and the vault's
   `agents/steward/scripts/quota-line.py`, which today expects a per-service
   `error` in place of `windows`.
4. Add tests for the 429 path.

## Acceptance

- A simulated 429 keeps the previous windows, marked stale with the error, and
  delays the next Claude request as the headers or the backoff say.
- Existing tests pass.

## Plan

1. Inspect one live response and kandev-pacer's cache. Record what can and
   cannot be established about this undocumented endpoint's limit.
2. Persist Claude's retry deadline and consecutive 429 count in the snapshot.
   Honor positive Retry-After seconds or HTTP dates; otherwise wait 10 minutes,
   doubling after each attempted 429 up to one hour. Skip Claude during the
   cooldown while continuing Codex and temperature collection.
3. Preserve the last successful Claude windows with last_success_at, stale,
   age_seconds and the existing error field. Read previous snapshots on each
   refresh so cooldowns and reading age survive restarts and one-shot runs.
4. Cover headers, backoff, repeated refreshes, recovery, missing prior data,
   and existing reader behavior with deterministic tests. Run the full suite,
   review the diff, merge to main, and complete the tracker without acceptance.
