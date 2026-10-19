Steward issue, 2026-10-19. Goal: agentic-leverage; pebble-quota is tier 1. Labelled `review`
(steward decision D68).

`docs/2026-09-19-architecture-review-and-remediation-plan.md` reviewed this
repository on 2026-09-19. 24 commits have landed since, and nobody has checked which
of its steps are done.

## What to do

1. For each finding and remediation step, check the current code on `main`:
   done (cite the commit), partly done, still open, or obsolete (say why).
2. Add a dated "Status, 2026-10-19" section to that document with the verdicts.
   Leave the original findings as they are.
3. Look at code added since the review for new over-engineering or shallow
   modules (the `honey-review` principles; deep modules in `codebase-design`
   terms). Add at most five new findings.
4. File each still-open or new step worth doing as an issue under `##
   Unverified proposals`, labelled `steward`, with `hai-tasks create` and a
   description that has acceptance criteria. The steward promotes those that fit
   Antti's goals.

## Constraints and acceptance

- Change no code. Run tests only where a verdict needs them.
- Every step of the plan has a verdict with evidence, and the tracker passes
  its own check if the Rules name one. Merge to `main` as the Rules describe.

## Execution plan, 2026-10-19

1. Compare main and its post-review history with every F1–F8 finding, ordered
   step and lower-priority item; distinguish source fixes from deployment and
   device verification. Preserve the original review text.
2. Inspect all post-review runtime changes for unnecessary layers or duplication.
   Run only offline checks needed to settle verdicts.
3. Append a dated status section with evidence and remaining acceptance gaps.
   Create distinct steward proposals through hai-tasks, with acceptance criteria
   and dependencies, without duplicating completed percentage/backoff issues.
4. Validate descriptions, links and the documentation-only diff; merge locally
   to main, remove the feature checkout/branch, and complete [5] pending acceptance.

## Delivery and validation, 2026-10-19

Appended `Status, 2026-10-19` to the original architecture report, preserving
its previous text byte-for-byte. All eight findings, eight ordered steps and
seven lower-priority entries have evidence-backed verdicts. F1 is fixed in
production source (9fff907, 5001e41); Step 1 retains test/operator/documentation
checks. F3/F8 are partly done; the other findings remain open. No obsolete or
new over-engineering finding was warranted by the full post-review diff.

Created nine steward-labelled candidates [6]–[14] with hai-tasks under
Unverified proposals, including acceptance criteria and dependency bullets/YAML.
Residual checks are included without reopening completed fixes or changing
acceptance. A create request referencing not-yet-created dependencies [13]/[14]
was rejected without a write; [12] was created with existing dependencies, then
updated through hai-tasks after [13]/[14] existed. Fresh reads verified all nine.

Validation: 35 unittest tests passed, zero failures/errors/skips; temporary
Python and Node assertions support the remaining source-level defects as
specified in the status section. No additional tests or runtime code were
committed. `git diff --check`, hai-tasks read, description/reference checks,
unique issue IDs, dependency frontmatter and preservation of all existing
issue fields passed. Tracker Rules specify no separate checker. Merge locally
to main and complete [5] with `[ ]`, leaving acceptance to the user/steward.
No deployment, service restart, production release or push is included.
