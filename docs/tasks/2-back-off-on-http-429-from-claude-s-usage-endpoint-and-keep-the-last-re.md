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

## Findings and implementation

- On 2026-10-17, one authenticated probe using pebble-quota's URL and headers
  returned 429, `Retry-After: 0`, and `rate_limit_error`. No other header whose
  name contained `retry`, `ratelimit` or `rate-limit` was present. Credentials
  were read only; no token refresh or extra probing was performed.
- The endpoint's throttle key remains unverified. A firsthand report in
  [upstream issue 31637](https://github.com/anthropics/claude-code/issues/31637)
  says per-access-token, but that is a community observation, not an official
  contract. Both local clients share that token, so shared throttling is
  plausible. The [public API rate-limit documentation](https://platform.claude.com/docs/en/api/rate-limits)
  describes organization/workspace inference limits and does not establish
  the subscription usage endpoint's key or polling allowance.
- kandev-pacer's provider uses the same endpoint with
  `?cedar_ember=1&skip_spend=1` and a Claude CLI user agent. It caches success
  for 300 seconds, failures for 15 seconds, and narrows success freshness to
  15 seconds when requested. Its separate success/error cache retains the
  success but does not apply 429-specific backoff or inspect Retry-After.
- Claude retry state is stored in latest.json as `retry_at` and
  `rate_limit_failures`. Positive Retry-After seconds or HTTP dates override
  the fallback of 600, 1200, 2400, then 3600 seconds. Zero, expired, invalid
  and out-of-range values use that fallback. The retry delay starts when
  the error response arrives. Refreshes during the cooldown make no Claude
  request and still collect Codex and temperature. Success clears retry state.
- Failed Claude reads retain the original windows and `last_success_at`,
  with `stale: true`, `age_seconds` and the existing per-service `error`.
  Older snapshots use their original collected_at for the first stale age.
  With no prior Claude reading, no windows or stale flag is fabricated.
  An initial 429 saves the cooldown even when neither provider has data.
- The watch payload's existing format continues delivering retained windows.
  The steward's existing windows/errors comprehensions accept the additive
  fields; the per-service error remains authoritative for stale readings.
  The watch firmware and vault script were not changed.

## Validation

- `python3 -m unittest discover -s tests -v`: 33 tests passed, including
  seven new tests for persisted cooldowns, numeric/date/invalid headers,
  exponential growth and cap, elapsed HTTP time, no previous reading,
  legacy reading age, simultaneous provider failure, recovery, and readers.
- `ruff check --select E9,F63,F7,F82 collector/pebble_quota.py tests/test_pebble_quota.py`
  and `git diff --check` passed.
- The environment's broader automatic Ruff and ty checks report existing
  collector diagnostics. Comparing the pre-change and current collector
  found the same diagnostic counts and codes; no unrelated cleanup was made.
