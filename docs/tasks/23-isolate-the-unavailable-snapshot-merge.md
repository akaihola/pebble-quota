Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D3 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Extract only the whole-snapshot fallback merge into a pure function with no disk, provider or clock access and no mutation of its inputs. `refresh_snapshot` keeps checkpoints, publication, the in-memory update before writes and the existing unavailable exception. Claude's per-provider retention and its timestamps are unchanged. If the open freshness proposal already supplies this seam, merge into it instead.

## Acceptance

- Pure cases keep the old quota, collection time and temperature, merge new attempts, cooldown and errors, and compute the same stale ages; an empty prior state stays unavailable; inputs stay unchanged.
- Integration tests, plus a retained-temperature case, tell apart both-failed with prior Claude from both-failed with only prior Codex, a first 429 without rows, restart interval suppression, and a write failure with new in-memory cooldown.
- Full offline checks pass; persisted schema and compact payloads are unchanged for those sequences. This does not complete the freshness proposal.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).
