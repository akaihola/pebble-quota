# Prevent older phone responses from overwriting data

Steward proposal, 2026-10-19, from architecture audit [5].
Promoted for implementation on 2026-10-24; deployment remains out of scope.

Lower-priority phone ordering/retry item. In a Node VM with delayed mocked
XHRs, completing at:200 then at:100 delivers 100 last. refresh has no generation
or freshness guard; AppMessage failure only logs.

## Acceptance criteria

- A minimal generation/in-flight/freshness policy prevents an older endpoint/token
  request or older quota response from overwriting the current generation's data.
  Keep legitimate recovery possible when clocks/timestamps are invalid.
- Node fixtures delay overlapping ready/watch/config requests, switch endpoint and
  token midflight, and complete callbacks in reverse order. Only valid current data
  reaches AppMessage; failed requests leave the last valid display intact.
- Reproduce transient AppMessage failure and choose a bounded retry or explicit
  deferred-until-next-refresh policy; document it and test no unbounded retry loop.
  Do not introduce a queue framework for the phone script.

## Steward note, 2026-10-24 12:45 refill

Promoted from Unverified proposals (steward D13, D95; goal
`agentic-leverage`, tier 1). Estimated 2–3 h. Tracker: [TASKS.md](../../TASKS.md).

- **Confirmed on `main` at `3bbc2c9`.** `refresh()` in
  `watchface/src/pkjs/index.js` starts a new request on `ready`, every
  `REFRESH_MS`, on `REQUEST_SYNC` and after `webviewclosed`, with no
  generation or freshness guard, so overlapping requests can finish in any
  order; `sendQuota()`'s failure callback only logs.
- **The dependency on [7] is dropped.** [7] wires these checks into CI. The
  checks themselves run locally: `tests/watch/phone.js` runs the phone script
  in a Node VM, and `PhoneContractTests` in `tests/test_pebble_quota.py`
  drives it. Extend that harness (for example to queue several requests and
  complete them in a chosen order); don't add a test framework or a CI run.
- **Out of scope:** the token in the configuration URL and the settings
  transport belong to [6], a security fix that stays with Antti; leave
  `configUrl()` and the stored-settings format as they are. The phone
  script's message keys and `latest.json` stay compatible with the installed
  watch.
- **No install or deploy.** Building the watch bundle as a check is fine;
  installing it on the watch is Antti's, and `pebble-quota.service` needs no
  restart for a phone-script change.
- Keep private paths and host names out of committed docs and code; the check
  receipt (`docs/tasks/14-….evidence.json`) is exempt.
- **Acceptance:** the three criteria above, each with a test that fails on
  `3bbc2c9` and passes after the change; all of `PhoneContractTests` and the
  existing unit tests, ruff and ty pass; the check receipt records them at the
  merged commit.

## Implementation plan

1. Give every refresh a sequence number; discard superseded callbacks even if
   the newer request fails. Snapshot endpoint/token and reset the timestamp
   watermark when either changes.
2. Reject decreasing collector timestamps for one refresh interval after the
   last forwarded response. Rejected responses do not extend that interval.
   Expiry or an invalid/backward phone clock allows recovery; malformed wire
   timestamps still fail validation. Equal timestamps remain deliverable.
3. Keep AppMessage failure deferred until the next ordinary refresh. Add an
   explicit failure log, with no retry timer or retained message queue.
4. Extend the existing Node VM fixture with delayed request completions,
   settings, clock and delivery outcomes. Test ordering, failures, recovery and
   bounded delivery; run the existing suite, Ruff and ty. Verify regressions
   against the audited baseline, then record checks at the merged commit.

## Implementation and validation

The [phone script] now snapshots settings and increments a refresh sequence at
request start. Only that sequence can send data. Within the same settings,
decreasing collector timestamps are rejected for one refresh interval after the
last forwarded response; rejections do not renew the interval. Equal timestamps
remain deliverable. Settings changes, interval expiry, and invalid or backward
phone clocks allow recovery. Invalid wire timestamps still fail whole-payload
validation. The watermark tracks forwarding attempts, including failed delivery;
this also bounds a failed future-dated reading's effect to one interval.

AppMessage failures explicitly defer until the next ordinary refresh, which
fetches current data. There are no delivery timers, retained messages or retries
inside the failure callback. The [watchface guide] documents this policy.

The [Node fixture] now controls ready/watch/timer/settings events, request
completion order, endpoint/token storage, phone time, and transient or persistent
AppMessage failures. [PhoneContractTests] covers:

- **Ordering:** reversed completions, a newer request with an older timestamp,
  timestamp-window expiry without renewal on rejection, and clock recovery.
- **Settings and failure:** endpoint-only and token-only switches invalidate
  pending requests and reset timestamp history. HTTP, network, timeout, malformed
  JSON and invalid timestamps preserve the last delivered display; a superseded
  success cannot revive after the newest request fails.
- **Delivery:** one transient failure recovers on the next refresh, including an
  equal timestamp; repeated failures produce only one attempt per refresh.
  A retry timer causes the fixture to fail immediately.

Before merge: all 106 unit tests passed (including all nine phone contract tests,
with Node and the C compiler available), and Ruff and ty passed. Three acceptance
regressions were run using the audited phone script at `3bbc2c9`: reversed
responses, timestamp regression, and explicit deferred delivery all failed as
expected; the regression probe exited zero after verifying these failures.
The initial baseline probe needed two harness corrections (the temporary watch
root lacked C sources, then subtest failures needed their parent test names).
These were probe setup errors; the corrected probe passed. No install, service
restart or CI change was performed. Diff review and whitespace checks passed.

## Memory guard before merge

Each guarded command used a 240-second timeout, ran alone, and was monitored
for the required memory and swap limits. Measurements are MiB; waits and elapsed
are seconds. Reports contain resource status only, not command output.

| Command | Outcome | Wait | Admission | Final | Starting swap | Swap growth | Elapsed | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline probe: initial setup | started at once | 0.0 | 11129.7 | 11092.5 | 1136.0 | 0.0 | 0.2 | exit 1 |
| Baseline probe: subtest setup | started at once | 0.0 | 11137.5 | 11130.1 | 1136.0 | 0.0 | 0.3 | exit 1 |
| Baseline regression verification | started at once | 0.0 | 11106.5 | 11077.0 | 1133.7 | 0.0 | 0.3 | exit 0 |
| `python3 -m unittest discover -s tests -v` | started at once | 0.0 | 11136.9 | 11072.4 | 1136.0 | -2.2 | 14.27 | exit 0 |
| `ruff check .` | started at once | 0.0 | 11064.6 | 11071.8 | 1133.7 | 0.0 | 0.1 | exit 0 |
| `ty check` | started at once | 0.0 | 11065.7 | 11101.2 | 1133.7 | 0.0 | 0.2 | exit 0 |

[phone script]: ../../watchface/src/pkjs/index.js
[watchface guide]: ../../watchface/README.md
[Node fixture]: ../../tests/watch/phone.js
[PhoneContractTests]: ../../tests/test_pebble_quota.py

## Checks at the merged commit

Merged commit: `e225b15301363c14bd05d5f0242925ebe1ccd00f`; base: `4426576a38ede15a2fbae59c6698eee09a26e5a4`.
Delivery commits, oldest first: `e225b15301363c14bd05d5f0242925ebe1ccd00f`. The task branch and worktree are
retained; checks ran with the task worktree clean and detached at this commit.
The [check receipt] contains the exact commands, tool hashes and results. This
project has no dependency lockfile or editable local package dependencies; its
checks use the standard library and the declared Python, Node, C, Git, Ruff and
ty executables.

- **Phone:** `python3 -m unittest discover -s tests -p test_pebble_quota.py -k PhoneContractTests -v`
  passed all nine tests, with no skips.
- **Unit:** `python3 -m unittest discover -s tests -v` passed all 106 tests,
  with no skips.
- **Lint:** `ruff check .` passed.
- **Types:** `ty check` passed.
- **Baseline:** the receipt's embedded baseline regression probe verified all
  three expected test failures on `3bbc2c9` and exited zero. The same tests pass
  in the phone and full-suite records above.

## Memory guard for evidence recording

Each command was `uv run <recorder> record <declaration> 'pebble-quota [14]'
<check-id>`, with full paths captured in the receipt. Each ran alone with a
240-second timeout and the required memory and swap monitoring. Measurements
are MiB; waits and elapsed are seconds.

| Check ID | Outcome | Wait | Admission | Final | Starting swap | Swap growth | Elapsed | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `phone` | started at once | 0.0 | 11090.8 | 11103.4 | 1133.7 | 0.0 | 2.61 | exit 0 |
| `unit` | started at once | 0.0 | 11103.6 | 11265.8 | 1133.7 | -0.3 | 14.46 | exit 0 |
| `ruff` | started at once | 0.0 | 11453.4 | 11451.6 | 1133.4 | 0.0 | 0.2 | exit 0 |
| `ty` | started at once | 0.0 | 11452.6 | 11452.9 | 1133.4 | 0.0 | 0.3 | exit 0 |
| `baseline` | started at once | 0.0 | 11450.1 | 11413.3 | 1133.4 | 0.0 | 0.5 | exit 0 |

All acceptance checks are recorded and passing. No owner action or agent-owned
follow-up remains for this issue. Completion is pending steward acceptance;
the acceptance checkbox remains unchecked.

[check receipt]: 14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.evidence.json
