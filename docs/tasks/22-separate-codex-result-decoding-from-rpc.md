Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D2 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Extract the rate-limit result parsing into one pure provider-specific function in `collector/pebble_quota.py`. Move value-only cases to direct calls; keep integration coverage of the handshake, notifications, deadline, environment and teardown. Keep the wrapped and direct formats, duration-based labels, sibling salvage and all diagnostic text.

## Acceptance

- Direct cases cover 0, 0.5, 1, 2, 100 and missing usage, bounded durations, a malformed primary with a valid secondary, an invalid result and legitimate no-window results; duplicate-duration behaviour and window order are unchanged.
- Fake-child tests still prove EOF, timeout and RPC errors, forced kill, reaping and closed pipes; a 1 % adapter result still compacts to `u: 1`.
- Full offline checks pass without invoking the installed Codex CLI or making a live quota request.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).
