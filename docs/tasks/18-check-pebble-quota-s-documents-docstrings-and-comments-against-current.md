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

## Execution record

Started on 2026-10-22 from main `ddb5723`; the active-state move was committed
immediately. Other task files, earlier reviews and the dated architecture
review remain unchanged. This section records this issue's work as required
by the launch instructions.

Plan:

1. Read the five in-scope Markdown files and all collector/watchface source
   comments; trace claims to implementation, configuration and tracker state.
2. Run the documented unittest command on unchanged main under the memory
   guard, then correct text and write the dated review with evidence and
   proposed answers for uncertainties.
3. Repeat the tests, verify executable content and tests are unchanged, check
   links and whitespace, merge into main, and complete the tracker unchecked.

Only one heavy command runs at a time. No authenticated provider, device,
emulator, phone or release run is part of this source review.

### Outcome and scope

Read all five eligible Markdown documents and all collector/watchface text
sources against main `9a572d2`. Corrected stale instructions and comments,
shortened the root entry point, and centralized the collector schema/settings
in the [collector reference]. The [documentation review] inventories every
document, lists changes with matching code, records uncertainties and ends with
one unfiled draft issue for checker policy. Existing proposals own the remaining
behavior and operational gaps; no new issue or thread was created.

Only documents, docstrings and comments changed. Other task files, previous
reviews, the dated architecture review, tests, build/release configuration and
executable content are unchanged. No formatting-only exception was needed.

### Checks

- **Main baseline:** `python3 -m unittest discover -s tests -v`, Python 3.14.7,
  66 passed, zero failures/errors/skips; suite time 15.887 seconds.
- **Final worktree:** the same command, 66 passed, zero failures/errors/skips;
  suite time 12.897 seconds. Compared all test identities and outcomes with the
  baseline; the test source is byte-identical.
- **Syntax and CLI:** `node --check watchface/src/pkjs/index.js` and
  `python3 collector/pebble_quota.py --help` passed before and after the edits.
- **Text-only proof:** Python AST comparison after removing docstrings matched
  main for the collector/build script; string-aware comment removal matched
  C/JS executable content. Git comparison confirmed protected files unchanged.
- **Document checks:** local relative links and heading anchors resolve;
  the generated PBW link is intentionally absent until a build. New/edited
  guide and review headings meet the 60-character limit. `git diff --check`
  passed. Temporary synthetic assertions with all providers mocked confirmed
  whole-snapshot temperature retention and the published example payload.
  The first reference-label helper misread explicit image references; after
  correcting the helper, all labels and 55 local links/anchors passed.
- **Existing checker failures:** the edit tool automatically ran Ruff and `ty`.
  Explicit `ruff check --output-format json` and `ty check --output-format concise`
  comparisons on the unchanged main collector and edited collector both exited
  1 with identical diagnostic identities: seven Ruff findings (`EXE001`, `UP035`,
  `PYI041`, four `BLE001`) and four type findings (optional timestamp subtraction,
  three server-attribute errors). These are not passing checks; no suppression
  or executable fix was made. The repository specifies only unittest validation,
  with no formatter/import-order rule. The review's D1 proposes a separate
  checker-policy decision for the steward.
- **Scope limits:** no PBW build, emulator/device/phone check, authenticated
  provider call, production restart or release run. Those would not establish
  this text-only change's unchanged behavior more directly than the source
  comparison and required tests; live compatibility and deployment remain
  explicitly unverified in the guides and existing proposals.

### Memory guard

Both heavy commands ran serially, under a 180-second execution timeout with
process-group cleanup. Admission waited for at least 2,048 MiB available (up to
600 seconds; fallback threshold 1,536 MiB). Monitoring every 0.2 seconds would
stop the command and children below 1,024 MiB or above 512 MiB swap growth.

- **Baseline suite — started at once.** Command:
  `python3 -m unittest discover -s tests -v`. Admission wait 0.00 seconds;
  admission MemAvailable 2,543.35 MiB; final 2,469.16 MiB. Starting swap use
  2,398.54 MiB; swap growth -3.75 MiB. Guarded execution elapsed 17.20 seconds;
  completion exit 0.
- **Final suite — started at once.** Command:
  `python3 -m unittest discover -s tests -v`. Admission wait 0.00 seconds;
  admission MemAvailable 2,378.50 MiB; final 2,412.85 MiB. Starting swap use
  2,372.63 MiB; swap growth -0.50 MiB. Guarded execution elapsed 14.00 seconds;
  completion exit 0.

### Handoff

No owner decision is required for this documentation change. The steward owns
the recorded follow-ups and acceptance; completion leaves the checkbox empty.
The branch and worktree remain after the local main merge. No push,
deployment, release or message to another person is part of this handoff.

Delivery commits: `ddb5723` committed the start move, `9a572d2` recorded the plan,
and `418b500` contains the reviewed text changes and evidence. Main fast-forwarded
to `418b500` after validation; the review is now on main. The final tracker move
is committed separately as `docs(tasks): complete HAI-18`, with acceptance left
unchecked.

[collector reference]: ../collector.md
[documentation review]: ../reviews/2026-10-22-docs-review.md
