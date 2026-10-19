---
depends-on: [7]
---

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
