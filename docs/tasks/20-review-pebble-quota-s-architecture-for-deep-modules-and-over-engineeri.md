Steward issue, 2026-10-22 06:17 refill (steward decisions D53 and D95: whole-repository architecture review aimed at simplification that keeps behaviour). Goal: agentic-leverage; pebble-quota, the quota source, is tier 1 in `<steward-vault>/Goals.md`. Label `review`. Estimated 1 h.

pebble-quota has never had a whole-repository architecture review. Its [2026-10-22 docs review](../reviews/2026-10-22-docs-review.md) and [2026-10-21 security review](../reviews/2026-10-21-security-review.md) already cover docs and security, and [19] has just cleared Ruff and ty.

## Work

1. Read `README.md`, `AGENTS.md` and `docs/`, then `collector/`, `watchface/` and `tests/` (`spikes/` only as far as current code depends on it).
2. Apply the `honey` principles (speculative generality, hand-rolled stdlib, single-caller abstractions, dead code, narration) and the `codebase-design` deep-module vocabulary, using those skills if your session has them: where a seam would make the collector's fetch, cache and serve paths smaller to change and easier to test, and what can be deleted.
3. Write `docs/reviews/2026-10-22-architecture-review.md`: findings ranked by benefit per hour, each with file and line evidence on `main`, what changes if it is fixed, and a drafted issue (title, work, acceptance, about an agent hour each). Mark drafts that overlap open issues or Unverified proposals in `TASKS.md` instead of duplicating them, and mark any draft that needs a phone, watch or live quota call to verify.

## Ground rules

- Architecture only. Don't probe for vulnerabilities, and make no request to Claude's or OpenAI's quota endpoints (the collector backs off on HTTP 429).
- Read-only apart from the report and this issue's tracker moves. Don't file the drafts; the steward files them.

## Acceptance

- Every finding cites code on `main` and says what changes if it is fixed.
- The report ends with a `## Draft issues` section and names the three drafts to do first, and why.
- Handoff: a short outcome; details go in the report and this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

[19]: 19-fix-the-seven-ruff-and-four-ty-findings-and-document-both-checks.md

## Implementation plan

1. Record the active move on canonical `main`, commit this plan, and rebase
   the review worktree. Pin the reviewed `main` commit for line evidence.
2. Read the guides and previous reviews, trace collector fetch, persistence,
   HTTP, phone and watch boundaries, and inspect the offline tests. Compare
   proposed work with all existing open and unverified tasks.
3. Write the [architecture report] with ranked findings, concrete behavior
   constraints, deletion opportunities and roughly one-hour draft issues.
   Use Honey and deep-module vocabulary; do not file or implement the drafts.
4. Check citations and overlaps, run appropriate offline validation under the
   required memory guard, and record evidence and limitations here. Merge only
   the report and this task record into `main`, then complete the tracker entry
   with acceptance unchecked. Keep the branch and worktree.

No provider calls, security probing, deployment, or unrelated edits are needed.

[architecture report]: ../reviews/2026-10-22-architecture-review.md
