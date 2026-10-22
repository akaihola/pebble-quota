# 001: Quota collectors — historical spike

**Question:** Could `gogo` obtain five-hour and weekly usage percentages and
reset times for Claude Code and Codex without screen scraping or exposing
credentials?

This records the original successful experiment. Use the [production collector]
and [collector guide] for current commands and behavior. The [prototype] is
preserved as historical code; it has not received the production percentage,
validation, cooldown, subprocess or security fixes.

## Original approach and result

Given authenticated Claude Code and Codex installations, the probe attempted to
emit normalized JSON with `used_fraction`, `resets_at` and `duration_seconds` for
each available window. It used Claude's undocumented OAuth usage endpoint and
Codex's local `account/rateLimits/read` JSON-RPC method.

The original run reported live Claude `5h` and `7d` windows and live Codex quota,
with no credentials observed in its output. That historical result does not
establish current CLI compatibility or guarantee safe output from the prototype:
its error path prints raw exception text.

Codex `primary` and `secondary` were not stable names for five-hour and weekly
windows. Only a 10,080-minute window was present on the tested account. This led
to labeling windows by `windowDurationMins`.

## Outcome

The recommendation to promote the experiment into a standard-library service
with a compact authenticated endpoint has been implemented in the [production
collector]. The prototype's magnitude-based percentage conversion remains
obsolete: it treats a provider value of `1` as a fraction rather than 1%.
No second production collector is maintained here.

[production collector]: ../../collector/pebble_quota.py
[collector guide]: ../../docs/collector.md
[prototype]: probe.py
