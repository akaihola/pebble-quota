Steward issue, 2026-10-22 07:16 refill (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 1 h.

This is draft D1 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there; read that draft and the finding it cites before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Compute `compact_watch` once in the watch route, validate its `q` and `at`, then serialize that object. Remove checks inside the compactor that its own normalization already guarantees. Keep the raw-input boundary, row order and truncation, timestamp and rounding rules, diagnostic categories, auth handling and public helper behaviour.

## Acceptance

- Authenticated loopback fixtures keep valid and mixed-valid payloads, accept timestamp zero, and return a fixed 503 for missing, corrupt, wrong-root, rowless and invalid-timestamp snapshots.
- Every serialized row is asserted valid, and valid siblings survive.
- Existing 401, 404 and config tests and all offline checks pass; the route no longer runs two independent normalization and publication paths.
- No live quota request, phone or watch is needed.

## Ground rules

- Behaviour stays the same unless the acceptance below says otherwise. Write the failing or pinning test first where the draft asks for one.
- Run at most one focused test command at a time, under your launch prompt's memory rule; no full browser suite.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

## Plan

1. Pin authenticated loopback publication behavior before editing production:
   valid/mixed rows, zero and invalid timestamps, missing/corrupt/wrong-root
   and rowless snapshots, fixed 503 body and sanitized diagnostic categories.
   Assert the complete serialized rows, ordering and truncation.
2. Compute one compact payload in the HTTP route, validate its rows and
   timestamp, and serialize it. Use normalized window fields directly inside
   the compactor; preserve public raw-input normalization and helper behavior.
3. Run focused HTTP/validation checks, the offline Python suite, Ruff, ty and
   JavaScript syntax checks sequentially under the memory guard. Review the
   diff, record results here, merge onto main and complete the tracker entry
   with acceptance unchecked.

The review's F1/D1 references were rechecked on current main: the duplicate
publication path remains at collector lines 689–693 and redundant compactor
checks at lines 534–538. No policy change is needed.
