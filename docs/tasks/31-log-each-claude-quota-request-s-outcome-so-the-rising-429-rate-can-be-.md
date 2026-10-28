Steward issue, 2026-10-28 10:26 refill (steward decisions D53 and D95). Goal: agentic-leverage (pebble-quota is tier 1 in `<steward-vault>/Goals.md`). Unlabelled. Estimated 1 h.

Tracker: [pebble-quota's tracker](../../TASKS.md).

## Why

kandev-pacer withholds every Claude launch while the collector's Claude reading is stale. Its status lines showed `WITHHOLDING` on 180 of 2,316 Claude lines on 10-26, 410 of 1,751 on 10-27, and about half of every hour on 10-28 from 00:00 to 10:00 (for example 66 of 113 at 02:00, 56 of 111 at 08:00), then none from 10:00. [kandev-pacer [205]][k205] now tolerates one stale reading for 15 minutes, but nobody can say why Claude reads fail more often since 10-26.

kandev-pacer [205]'s investigation (its task record, "Collector journal investigation") found that the collector cannot answer this: it catches each provider exception into the current snapshot, journals nothing per Claude attempt, and the snapshot overwrites history. Its journal errors on 10-27 were generic `OSError` messages naming no provider or HTTP status. Two changes went live on the evening of 10-26 and are both possible causes: this repository's [[30]][p30] (`30f20eb`, the usage request now asks for reset-grant metadata, restarted 19:01) and kandev-pacer's shared polling of this collector (live 19:11). The cause is unresolved; this issue makes the next answer possible.

## What to do

1. Log one line per actual Claude usage request to the service's journal (stderr), with: provider, outcome (`ok`, the HTTP status, or an error class such as timeout, connection or parse error), attempt time, the service's previous `last_success_at`, the persisted `retry_at` after the attempt, and the `Retry-After` value when the response had one. Use a fixed, greppable prefix (for example `claude attempt:`) and one key=value or JSON form documented in `docs/collector.md`.
2. Log a skipped Claude attempt (inside the refresh interval or before `retry_at`) separately and at most once per refresh pass, so skips are never counted as failures.
3. Never log tokens, headers, request URLs with credentials, response bodies or unrelated provider fields. A test proves that a response body and an authorization header value never reach the log.
4. Add offline tests for a success, a 429 with and without `Retry-After`, a non-429 HTTP error, a network error and a skip. Keep the existing snapshot format, stale handling and 429 cooldown unchanged; the existing tests must pass unchanged.
5. Document the log line and a one-line daily count command in `docs/collector.md`.

## Constraints

- No live request beyond the collector's own polling, no service restart and no change to the installed service or its configuration; the steward restarts the collector after merge and reads a day of counts.
- Keep private paths and host names out of committed docs and code; the check receipt is exempt.
- Memory: follow your launch prompt's memory rule.

## Acceptance

- Steps 1–5 are on `main`; the new tests pass and the full offline suite, Ruff, ty and whitespace checks pass, and the check receipt records them.
- Handoff: a short outcome; details go in this task record.

[k205]: http://tinni/prg/kandev-pacer/docs/tasks/205-keep-using-claude-s-last-good-pebble-reading-for-up-to-15-minutes-afte.md?f
[p30]: 30-include-claude-reset-grants-in-quota-snapshots.md
