Steward issue, 2026-10-25 00:17 refill (steward decisions D53 and D95). Goal: agentic-leverage (pebble-quota is a tier 1 project in `<steward-vault>/Goals.md`). Estimated 0.75 h.

Tracker: [TASKS.md](../../TASKS.md).

Draft D1 of [the simplification review](../reviews/2026-10-25-simplification-review.md) ([27], finding F1). Four tests repeat the same loopback HTTP server lifecycle (`tests/test_pebble_quota.py` 422–437, 447–476, 1129–1135 with 1200–1203, and 1566–1573 at `3a963b0`), and the pipeline helper's `view(watch_now=...)` option has no caller that uses it. One helper makes the tests shorter without touching production code.

## What to do

1. Add one local `contextlib.contextmanager` in `tests/test_pebble_quota.py` that takes the snapshot path and token, binds the existing server to loopback on port zero, yields the server, and shuts it down, closes and joins it in `finally`.
2. Use it in the two `HttpTests` methods, `ValidationTests.test_http_damaged_state_and_diagnostics_are_sanitized` and `WatchPipelineTests.setUp`. Server cleanup must still run before the temporary files and mocks go away.
3. Remove `view(watch_now=...)` and always use `self.now` there.
4. Leave the socket-only busy-port test, the provider fixtures and `WatchTools` unchanged. Don't widen subprocess or network permissions.

## Checks that show behaviour is kept

- `HttpTests.test_config_page_served_without_auth`, `HttpTests.test_watch_endpoint_requires_bearer_token`, `ValidationTests.test_http_damaged_state_and_diagnostics_are_sanitized`, `StartupTests.test_busy_port_does_not_collect` and all `WatchPipelineTests`, in particular `test_healthy_claude_429_cooldown_and_recovery`, `test_offline_phone_ages_rows_and_temperature`, `test_reset_crossing_hides_old_usage_even_when_recent`, `test_future_timestamps_beyond_the_skew_are_not_fresh` and `test_missing_temperature_and_colour_follows_the_marker`. Node and the host C compiler must be present so the pipeline tests run rather than skip.
- The full offline suite, `ruff check .` and `ty check`.
- Read the helper's `finally` and context lifetimes once more to confirm cleanup still runs when an assertion fails.

## Constraints

- Test-only: change only `tests/test_pebble_quota.py`, besides this issue's own moves. No production file, protocol, publication policy or provider-access guard changes.
- Don't restart the collector or any service, and make no request to a real provider: the test suite's network guard must stay on.
- Memory: follow your launch prompt's memory rule; run one heavy command at a time and stop every process you start.
- Keep private paths out of committed docs and code; the check receipt is exempt.
- If a formatting-only change is demanded by a required check, make it and say so.

## Acceptance

All named tests keep their assertions and pass without skips; the four lifecycle copies become one; every `view` caller stays valid; the server still shuts down, closes and joins within its existing teardown; net test source is smaller. No deployment, device check or real provider request. Handoff: a short outcome; details stay in this file.

[27]: 27-review-pebble-quota-s-changes-since-the-10-22-architecture-review-for-.md

## Implementation plan

Use one context manager for the four server lifetimes, with shutdown, close
and thread join in its `finally`. Nest the HTTP contexts inside temporary
directories; register the pipeline context after its mocks so LIFO cleanup
stops the server first. Remove the unused `watch_now` argument. Preserve all
assertions, provider guards, socket-only tests and tool fixtures. Run the named
checks, the full offline suite, Ruff and ty, then review cleanup on failure.

## Implementation and review

One `loopback_server(snapshot, token)` context manager replaces all four
lifecycles. `view()` always uses `self.now`; all callers take no arguments.
The test source is 18 lines smaller. AST comparison confirmed every assertion
is unchanged, as are `setUpModule`, `WatchTools` and `StartupTests`. Provider
fixtures and access permissions are unchanged. No formatting-only changes.

Reviewed the helper `finally`: shutdown, close and join (two-second timeout)
run when a test assertion raises. The three HTTP contexts are inside their
temporary directories. Pipeline `enterContext` registers cleanup after the
mocks and temporary directory, so LIFO cleanup stops the server first,
including after a setup or assertion failure.

Pre-merge validation: 106 offline tests passed, no skips, with Node and the
host C compiler present; Ruff and ty passed. No service or provider access.

## Memory reports before merge

- `python3 -m unittest discover -s tests -v`: started at once; wait 0.0 s; MemAvailable admission/final 58088/58083 MiB; starting swap 0 MiB, growth 0 MiB; elapsed 14.24 s; exit 0.
- `ruff check .`: started at once; wait 0.0 s; MemAvailable admission/final 58087/58094 MiB; starting swap 0 MiB, growth 0 MiB; elapsed 0.2 s; exit 0.
- `ty check`: started at once; wait 0.0 s; MemAvailable admission/final 58093/58092 MiB; starting swap 0 MiB, growth 0 MiB; elapsed 0.2 s; exit 0.
