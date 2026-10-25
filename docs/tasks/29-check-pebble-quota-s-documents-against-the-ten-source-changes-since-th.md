Steward issue, 2026-10-25 02:43 refill (steward decisions D43, D68 and D95). Goal: agentic-leverage (pebble-quota is tier 1 in the steward vault's `pages/Goals.md`: it is the quota source). Labelled `review`. Estimated 1 h.

## Why

[The 2026-10-22 docs review](../reviews/2026-10-22-docs-review.md) matched the documents to the code at `418b500`. Since then ten source commits changed pebble-quota: Ruff and ty findings cleared and both checks documented, one compact payload decision for HTTP, Codex result decoding separated from RPC, the unavailable-snapshot merge isolated, unused collector generality removed, freshness and failure status carried to the watch, the five-line collector, phone and watch contract enforced, zero-byte string tuples rejected on the watch, superseded phone responses discarded with a bounded freshness guard, and one shared loopback test server. The steward and the pacer read the collector's output every few minutes, so a stale statement about it misleads both.

## What to do

1. List the source commits since `418b500` (`git log --no-merges --reverse 418b500..main -- . ':!docs' ':!*.md'`) and, for each, what it changed in behaviour, payload fields, settings, files written or messages.
2. Read `README.md`, `AGENTS.md` and `docs/collector.md` against current `main` for those changes. Leave the dated `docs/2026-09-19-architecture-review-and-remediation-plan.md` as it is.
3. Fix plain discrepancies and stale statements. Where two documents explain the same thing, keep one explanation and link to it from the other. Prefer shorter text: delete statements the code no longer supports rather than adding caveats.
4. Where it's unclear whether the code or the text is wrong, don't guess: list it with the evidence and a proposed answer in `docs/reviews/<run date>-docs-recheck.md`. That file also lists each change you made, by document, with the commit or code it now matches, and ends with a `## Draft issues` section for anything larger than a documentation fix. Don't file those issues; the steward decides.

## Constraints

- Documentation only: no code or test changes, except a formatting-only change a required check demands. Leave task files and earlier reviews as they are.
- Don't restart the collector, rebuild or install the watch or phone app, or touch credentials or live configuration.
- Keep private paths out of committed docs and code; the check receipt is exempt.
- Memory: follow your launch prompt's memory rule. Run one heavy command at a time.

## Acceptance

- The review file is on `main`, every document named in step 2 was read, and each change it lists names the commit or code it now matches.
- The diff touches only Markdown outside `docs/tasks/` and `docs/reviews/`, plus this task's record and the new review file.
- The checks `AGENTS.md` asks for pass before merging. Handoff: a short outcome; details go in the review file and this task record.

Tracker: [pebble-quota's tracker](../../TASKS.md).

## Implementation plan

1. Enumerate source commits after `418b500` and compare their changes with the
   [project entry point], [agent instructions] and [collector reference]. Read
   the affected source and tests; keep historical reviews unchanged.
2. Correct factual discrepancies and replace duplicated explanations with
   links. Record commit-by-commit coverage, document changes and unresolved
   questions in the [documentation recheck], ending with draft issues only.
3. Run the documented offline suite, Ruff and ty sequentially under the memory
   guard. Check Markdown links, change scope and whitespace. Merge to `main`,
   record those checks from the clean merged commit, and complete the tracker
   entry without accepting it.

[project entry point]: ../../README.md
[agent instructions]: ../../AGENTS.md
[collector reference]: ../collector.md
[documentation recheck]: ../reviews/2026-10-25-docs-recheck.md
