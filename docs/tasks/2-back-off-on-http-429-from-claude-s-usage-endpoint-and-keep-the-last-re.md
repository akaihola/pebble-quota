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

## Research note, 2026-10-21

Bounded follow-up for [the usage-limit research task]. **The throttle key
cannot be established from the reviewed public sources and existing local
records.** Per-access-token throttling is a reported hypothesis; account or
source-address throttling, combined limits, and a fixed polling allowance
remain unverified. This note proposes a scope correction, not a claim that
work step 1's original identification requirement has been met.

### Public evidence

- **Official documentation:** Anthropic's [API rate-limit documentation]
  describes organization/workspace limits and Messages API request/token
  rates. It explains `retry-after` and rate-limit response headers, but does
  not specify a throttle key, bucket size, refill period or supported polling
  interval for `GET https://api.anthropic.com/api/oauth/usage`. Its inference
  limits cannot establish this subscription metadata endpoint's contract.
  Targeted searches of the platform and Claude Code documentation found no
  such contract; that is a bounded search result, not proof none exists.
- **Firsthand report:** prakersh's 2026-03-07 comment in [upstream issue
  31637] claims a fresh access token receives approximately five requests
  before 429. GiGurra reports the suggested token-refresh workaround breaks
  Claude Code's refresh behavior. Another contributor reports persistent
  429 at ten-minute intervals and after thirty-minute backoff. These are
  community observations, without provider confirmation or a controlled
  comparison isolating identity from elapsed time and other clients.
- **Conflicting client claims:** [claude-web-usage's project documentation]
  says the bucket is per-token rather than per-IP; [AgentGauge's project
  documentation] describes a shared account/IP bucket. Neither provides a
  provider contract or enough comparative evidence to settle that conflict.
  Treat both as client authors' claims, not established server behavior.

Sources were read on 2026-10-21. No workaround, token refresh or usage-endpoint
request from these sources was executed.

### Existing local records

Read the [steward quota history] and its [snapshot recording script], the
[collector service configuration], the [collector implementation] and
[kandev-pacer's provider implementation]. Only timestamps, error categories
and scheduling metadata were extracted; no credentials or raw HTTP payloads
were read. The steward history had 43 valid JSON lines, from 2026-10-16
16:46:10 through 2026-10-21 11:01:18 UTC: nine Claude 429 samples, 34 samples
without service errors, and no other recorded service errors.

The following are snapshot `collected_at` times, truncated to seconds, all
UTC. Adjacent error-free samples bound observations, not the actual start
or end of a lockout:

- **October 17:** error-free October 16 22:59:20; 429 at 02:00:05 and
  05:00:49; error-free 07:16:26.
- **October 19–20:** error-free October 19 13:59:03; 429 at 16:59:16,
  19:58:43, 22:58:21 and October 20 01:57:36; error-free 04:56:45.
- **October 20:** error-free 19:28:36; 429 at 20:00:02 and 22:09:23;
  error-free 22:40:16.
- **October 21:** error-free 04:56:52; 429 at 09:09:17;
  error-free 10:57:13. The existing [collector snapshot] was also successful
  at 12:30:05 when inspected; it contained no retry state or attempt timestamp.

The steward script's `t` is the time it reads the snapshot; `collected_at`
is the collector pass time. Neither necessarily dates the failed request:
backoff preserves the earlier error during skipped refreshes. Sampling gaps
in this history range from 29m11s to 15h00m54s, usually around three hours.
Thus nine error samples are **not nine observed HTTP requests**, nor proof of
continuous failures between them. The October 19–20 error observations span
almost nine hours, but successes between samples cannot be excluded.

The service is configured with `--refresh-seconds 300`. The collector waits
300 seconds after each refresh finishes, so healthy attempts are about five
minutes apart plus collection time, rather than a precise five-minute clock.
The implemented 429 fallback delays are 600, 1200, 2400 and then 3600 seconds,
with the next attempt on an eligible refresh. Five-minute snapshot updates
can therefore repeat a 429 while no Claude request occurs. This history
cannot measure requests per minute, identify a refill/reset interval, prove
five-minute polling is safe, or attribute failures to this collector alone.

The retained user journal was inspected with:

```bash
journalctl --user -u pebble-quota.service \
  --since '2026-10-16 00:00:00 UTC' \
  --until '2026-10-21 12:35:00 UTC' -o json --no-pager
```

Only one entry was available: a service start at October 18 17:48:32 UTC;
there were no retained 429 or request/response entries. The collector stores
per-provider failures in the snapshot and logs refresh-level exceptions, so
journal silence does not establish successful requests. The snapshot is
overwritten, and the steward history omits headers, retry deadlines, failure
counts and request identity. The earlier 2026-10-17 probe recorded above
remains the only saved header evidence reviewed here: 429, `Retry-After: 0`,
no other matching rate-limit headers. It was not repeated.

The local pacer source can also fetch the same OAuth endpoint (with query
parameters and a different user agent), including a direct supplement to
readable Pebble data. Its cache permits 300-second normal freshness,
15-second fresh reads and 15-second failure caching. That demonstrates a
possible additional caller, not its historical request count. No complete
caller timeline or sanitized token/account/address identifiers exist in the
reviewed records. Shared failures cannot distinguish a shared token from a
shared account, address or overlapping server limits.

### Proposed scope correction

Replace work step 1 and plan step 1 with this bounded requirement:

> Review official documentation, firsthand public reports and existing
> sanitized records for the OAuth usage endpoint's throttling behavior.
> Record supported observations and unknowns. If the key or numeric allowance
> is unpublished or cannot be isolated from those records, state it as
> unverified; do not require live probes, token rotation or limit exhaustion.
> Retain the recorded Retry-After evidence and assess the backoff through
> deterministic tests, without claiming it guarantees provider acceptance.

**Recommendation:** Review this task's existing functional acceptance
criteria under that corrected research scope. Leave the throttle key and
supported polling budget explicitly unknown. Establishing either would need
an authoritative provider statement or pre-existing, sufficiently complete
request records distinguishing callers and identities; collecting that
instrumentation would be separately scoped work. This proposal does not
accept this task, change its acceptance checkbox, or re-run its earlier tests.

### Follow-up validation

Research changed documentation only. Counts and timestamp groups were checked
against all 43 saved history lines; local links and `git diff --check` were
validated. No live provider request, credential read, service restart, code
change or test-suite run was needed.

[the usage-limit research task]: 17-find-what-claude-s-usage-endpoint-rate-limits-on-from-public-sources-a.md
[API rate-limit documentation]: https://platform.claude.com/docs/en/api/rate-limits
[upstream issue 31637]: https://github.com/anthropics/claude-code/issues/31637
[claude-web-usage's project documentation]: https://github.com/skibidiskib/claude-web-usage/blob/main/README.md#the-problem
[AgentGauge's project documentation]: https://github.com/ghostface2232/AgentGauge/blob/main/AGENTS.md#endpoint-rate-limiting-important
[steward quota history]: http://hopeli/my-knowledge/agents/steward/quota.jsonl?f
[snapshot recording script]: http://hopeli/my-knowledge/agents/steward/scripts/quota-line.py?f
[collector service configuration]: http://hopeli/.config/systemd/user/pebble-quota.service?f
[collector implementation]: ../../collector/pebble_quota.py
[kandev-pacer's provider implementation]: http://hopeli/prg/kandev-pacer/src/kandev_pacer/provider.py?f
[collector snapshot]: http://hopeli/.local/state/pebble-quota/latest.json?f
