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


## Implementation plan

- Capture request start and response Retry-After at the Claude HTTP boundary;
  emit an allowlisted JSON journal record after cooldown calculation.
- Emit separate refresh/cooldown skips, without changing snapshot fields,
  retention or backoff behavior.
- Add offline outcome and redaction coverage, document the format and daily
  counts, then validate, merge and record checks at the delivery commit.

## Delivery notes

Implemented request and skip stderr records in the [collector], with offline
coverage in the [test suite] and operator instructions in the [collector guide].
No live provider requests, service restart or installed configuration changes.
The steward reported restarting at 11:03:47 on 2026-10-28 to load the logging;
next-day outcome counts remain with the steward. No restart was performed here.

[collector]: ../../collector/pebble_quota.py
[test suite]: ../../tests/test_pebble_quota.py
[collector guide]: ../collector.md

## Review and preliminary validation

Reviewed the diff: no snapshot fields, stale retention or cooldown calculations
changed; existing tests were left intact. HTTP metadata is captured before
JSON parsing, so malformed responses and HTTP errors are counted. Preflight
failures do not impersonate HTTP requests. Retry-After dates/numbers are
normalized before logging to avoid echoing arbitrary header text.

The preliminary full offline suite passed (117 tests); Ruff, ty and whitespace
checks also passed. Final merged-commit checks and receipt follow below.

### Memory reports

| Command | Outcome | Wait | Admission / final MiB | Initial swap / growth MiB | Elapsed | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `python3 -m unittest discover -s tests -v` | started at once | 0 s | 56061 / 55877 | 10 / 0 | 14.78 s | exit 0 |
| `python3 -m unittest discover -s tests -v && ruff check . && ty check && git diff --check` | started at once | 0 s | 56082 / 56036 | 10 / 0 | 14.78 s | exit 0 |

Final pre-merge validation passed: 118 offline tests, Ruff, ty and whitespace.

## Merged delivery and check receipt

The 11:00 steward review identified that the daily-count example selected the
system journal while the installed collector is a user unit. The [collector
guide] now uses `journalctl --user -u pebble-quota.service`; a short clause
explains that system-unit installs drop `--user`. This correction changes only
documentation. No code or tests changed and no service was restarted.

Base: `3390354e0fafb373c2f8d2ac59a4537abba2e78c`. Delivery commit (oldest first):
`127660a84ba0846ad707ef75691ec432f3a96170`. Fast-forwarded onto `main`; branch and
worktree retained. Acceptance remains unchecked for the steward.

A fresh [check receipt] records the same five checks at the merged commit in
a clean detached task worktree. All passed. No lockfile or editable local
dependencies apply; dependency declarations remain empty.

- **claude-outcomes:** `PYTHONPATH=tests python3 -m unittest -v test_pebble_quota.ClaudeBackoffTests` — exit 0 (14 tests).
- **offline-suite:** `python3 -m unittest discover -s tests -v` — exit 0 (118 tests).
- **ruff:** `ruff check .` — exit 0.
- **ty:** `ty check` — exit 0.
- **whitespace:** `git diff --check 3390354e0fafb373c2f8d2ac59a4537abba2e78c 127660a84ba0846ad707ef75691ec432f3a96170` — exit 0.

### Correction recording memory reports

Each row names an evidence-recorder invocation (`uv run` with `record`, this
issue and the check ID). The declaration and logs stayed outside the clean
checkout.

| Recorder check | Outcome | Wait | Admission / final MiB | Initial swap / growth MiB | Elapsed | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `record claude-outcomes` | started at once | 0.0 s | 55848 / 55817 | 10 / 0 | 0.25 s | exit 0 |
| `record offline-suite` | started at once | 0.0 s | 55851 / 55743 | 10 / 0 | 15.03 s | exit 0 |
| `record ruff` | started at once | 0.0 s | 55751 / 55748 | 10 / 0 | 0.25 s | exit 0 |
| `record ty` | started at once | 0.0 s | 55762 / 55767 | 10 / 0 | 0.25 s | exit 0 |
| `record whitespace` | started at once | 0.0 s | 55766 / 55762 | 10 / 0 | 0.25 s | exit 0 |

## Initial delivery history

Base: `668db6899650d257450b6bac97d0af69ef11ac14`. Delivery commit (oldest first):
`220aeaa3eee5ae1593acefb6357d4961c9bebefb`. Fast-forwarded onto `main`; branch and
worktree retained. Acceptance remains unchecked for the steward.

All five checks passed at the initial delivery commit in a clean detached task
worktree. The current [check receipt] supersedes that initial receipt. No lockfile or editable local dependencies exist in this stdlib-only
project, so dependency declarations are empty.

- **claude-outcomes:** `PYTHONPATH=tests python3 -m unittest -v test_pebble_quota.ClaudeBackoffTests` — exit 0 (14 tests, including seven new logging tests).
- **offline-suite:** `python3 -m unittest discover -s tests -v` — exit 0 (118 tests).
- **ruff:** `ruff check .` — exit 0.
- **ty:** `ty check` — exit 0.
- **whitespace:** `git diff --check 668db6899650d257450b6bac97d0af69ef11ac14 220aeaa3eee5ae1593acefb6357d4961c9bebefb` — exit 0.

### Recording memory reports

Each row names one invocation of the evidence recorder (`uv run` with its
`record` subcommand, this issue and the check ID); the declaration and logs
stayed outside the clean checkout. Commands and paths are in the receipt.

| Recorder check | Outcome | Wait | Admission / final MiB | Initial swap / growth MiB | Elapsed | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `record claude-outcomes` | started at once | 0.0 s | 56023 / 55993 | 10 / 0 | 0.25 s | exit 0 |
| `record offline-suite` | started at once | 0.0 s | 56063 / 56015 | 10 / 0 | 14.78 s | exit 0 |
| `record ruff` | started at once | 0.0 s | 56039 / 56037 | 10 / 0 | 0.25 s | exit 0 |
| `record ty` | started at once | 0.0 s | 56030 / 56049 | 10 / 0 | 0.25 s | exit 0 |
| `record whitespace` | started at once | 0.0 s | 56049 / 56047 | 10 / 0 | 0.25 s | exit 0 |

The steward owns next-day count review; there is no owner decision or
agent-owned implementation gap.

[check receipt]: 31-log-each-claude-quota-request-s-outcome-so-the-rising-429-rate-can-be-.evidence.json
