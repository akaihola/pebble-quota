Steward issue, 2026-10-22 08:00 digest (steward decisions D53 and D95: simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota is tier 1 in `<steward-vault>/Goals.md`. Estimated 45 min.

This is draft D5 of [the 2026-10-22 architecture review](../reviews/2026-10-22-architecture-review.md#draft-issues), filed as written there now that its prerequisite D1 ([21]) is done; read that draft and the finding it cites (F5) before starting. The review's line numbers refer to the commit it names; recheck them on current `main`.

## Work

Make the HTTP handler a directly named class and update repository call sites. Narrow `iso_from_epoch` to numeric epoch formatting and remove its unused `None` and string branches. Keep its name, fractional-second support, datetime formatting and range-error behaviour. Don't change the snapshot reader's accepted ISO timestamps or the typed server attributes.

## Acceptance

- A caller search confirms the removed inputs and the factory customization are unused in this repository.
- Existing cooldown, HTTP, corrupt-snapshot, out-of-range Retry-After and fractional HA-age tests pass; Ruff and ty stay clean.
- A small numeric formatting assertion preserves zero and fractional epochs.
- No change to routes, headers, disk format or emitted JSON. No live quota request, phone or watch is needed.

## Ground rules

- Behaviour stays the same unless the acceptance above says otherwise. Write the pinning test first.
- Run at most one focused test command at a time, under your launch prompt's memory rule.
- Keep private paths and host names out of committed files (the docs tests reject them).
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).
