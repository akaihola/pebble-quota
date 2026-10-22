Steward issue, 2026-10-22 04:23 refill. Goal: agentic-leverage (pebble-quota is tier 1, the quota source). Labelled `review` (steward D68). Estimated 45 min.

48 commits have landed on `main` since 2026-10-19, including the 10-21 security review's fixes and the Codex RPC fix of 10-22. Each issue updated the documents only where it touched them, so statements elsewhere may now be stale or in conflict. pebble-quota has had a security review but never a documentation check. It has few documents, so this check also covers docstrings and comments. The same check has run for kandev-pacer, Hai, Filemill, pi-akaihola, mailjail, kandev-config, skills-akaihola, iskumetri, dallape and syncop.

## What to do

1. Read every tracked Markdown file outside `docs/tasks/`, `docs/reviews/` and `TASKS.md` (`git ls-files '*.md'`), `README.md` and `AGENTS.md` first, against the code on current `main`: commands, settings and their defaults, file layout, the collector's output format, how to build, run and test, and what each document says is done or planned.
2. Read the docstrings and comments of the collector and watchface sources (`git ls-files collector watchface`) for statements the code no longer bears out: parameters, return values, units, defaults, invariants.
3. Fix plain discrepancies and stale statements in text only. Where two places explain the same thing, keep one and link to it. Keep entry points short.
4. Where it's unclear whether the code or the text is wrong, don't guess: list it in `docs/reviews/<run date>-docs-review.md` with the evidence and a proposed answer.
5. That file also lists each change you made, by file, with the code it now matches, and ends with a `## Draft issues` section for anything larger than a text fix. Don't file those issues; the steward decides.

## Constraints and acceptance

- Text only: documents, docstrings and comments. No change to code behaviour or tests. A formatting-only change that a required check (formatter, import order) demands is allowed; say so in the task record. Leave task files, earlier reviews and the dated architecture review as they are.
- No device, watch, phone or release run; this is a source and text check.
- Before merging, run the tests and checks the Rules and `AGENTS.md` (or the README) ask for, and show they pass unchanged.
- Memory: follow your launch prompt's memory rule, and run one heavy command (test suite, browser, build) at a time.
- Handoff: a short outcome and the checks run; detail goes in the review file and this task record.
- Acceptance: the review file is on `main`, every document named in step 1 was read, each change it lists names the code it now matches, and the test results match `main` before the change.

Tracker: [the pebble-quota tracker](../../TASKS.md).
