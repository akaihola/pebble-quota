# Prevent older phone responses from overwriting newer settings or data

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

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
