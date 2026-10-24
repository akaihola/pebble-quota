Steward issue, 2026-10-24 23:50 refill (steward decisions D53, D68 and D95). Goal: agentic-leverage (pebble-quota is a tier 1 project in `<steward-vault>/Goals.md`). Labelled `review`. Estimated 1 h.

Tracker: [TASKS.md](../../TASKS.md).

[The architecture review](../reviews/2026-10-22-architecture-review.md) ([20]) read `main` at `61ebe07`. Its drafts D1, D2, D3 and D5 are finished as [21]–[24]. Since then `main` has gained four more commits besides tracker moves: freshness and failure status carried through to the watch (`20644d3`), the five-line collector, phone and watch contract ([11], `c9de5a5`), zero-byte watch strings rejected ([26]) and superseded phone responses discarded ([14]). Outside `docs/` and `TASKS.md`, 11 files changed (about 1,815 lines added, 358 removed): about 1,000 in `tests/`, the rest in `collector/pebble_quota.py`, the new `watchface/src/c/gauges.c` and `gauges.h`, `watchface/src/c/watchface.c` and `watchface/src/pkjs/index.js`. Features added one at a time may repeat a decision, keep a path that a later change made obsolete, or add machinery that a smaller change would replace. This issue looks for exactly that, so that agents can simplify pebble-quota without changing what it does.

## What to do

1. Record `main`'s commit. Read the code added or changed since `61ebe07` (`git diff 61ebe07 main -- . ':!docs' ':!TASKS.md'`), the four feature commits first.
2. Look for simplifications that keep behaviour: duplicated decisions or helpers within one layer, values one layer computes and the next recomputes, code paths no caller reaches any more (check callers and tests, not names alone), state or options that only one test uses, test helpers repeated across the new tests, and verbose code that a shorter standard form would replace. Each layer validating its own input (collector, phone, watch) is intended; don't count that as duplication. Apply the `honey` principles and the `codebase-design` deep-module vocabulary where they are installed. Cite files and lines at the recorded commit. Confirm each finding by reading its callers and tests; leave out anything you can't confirm.
3. Leave security questions out: [16] holds the security review's fixes.
4. Write the result as `docs/reviews/YYYY-MM-DD-simplification-review.md`, dated the day you write it: the commit checked, the findings ranked by lines removed and risk, and "Do these first" (at most three). If you find nothing worth doing, say so in the report; that is a valid outcome.
5. Under a final "Draft issues" heading, draft one issue per finding worth doing: title, why, what to change, the checks that show behaviour is kept (name the existing tests, or the test to add first), and acceptance. Group small related findings into one issue. Don't file them; the steward does. Leave out any that an open issue already covers, and name that issue.

## Constraints and acceptance

- Documentation only: no code, test or tracker changes besides this issue's own moves.
- Don't restart the collector or any service, and make no request to a real provider: the test suite's network guard must stay on.
- Memory: follow your launch prompt's memory rule; run one heavy command at a time and stop every process you start.
- Keep private paths out of committed docs; the check receipt is exempt.
- If a formatting-only change is demanded by a required check, make it and say so.
- Acceptance: the report names the commit it checked; every finding cites file and line and says how it was confirmed; each draft issue names the checks that show behaviour is kept. Handoff: a short outcome; details stay in the report.

[11]: 11-enforce-the-five-row-collector-phone-and-watch-contract.md
[14]: 14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.md
[16]: 16-fix-the-collector-and-build-findings-of-the-2026-10-21-security-review.md
[20]: 20-review-pebble-quota-s-architecture-for-deep-modules-and-over-engineeri.md
[21]: 21-use-one-compact-payload-decision-for-http.md
[24]: 24-remove-unused-collector-helper-generality.md
[26]: 26-reject-zero-byte-watch-strings-before-replacing-rows.md

## Review plan, 2026-10-25

Review `main` at `3a963b0df7dc941ce80598082e0b6705b258718c`, against
`61ebe07c4ba9e377f14980ceee761dcd284e68d1`. Read the freshness, five-row,
zero-byte string and response-ordering commits first, then the combined diff.
Trace each candidate through its callers and tests, preserving validation at
each layer; compare candidates with open issues before drafting anything.

Write the dated report with ranked, line-cited findings, at most three first
actions and unfiled draft issues naming preservation checks. Review the report
for accurate citations, relative links and absence of private paths. Run the
documented offline suite, Ruff and ty with the network guard enabled and the
required memory guard; change only this report and this issue's records.
Rebase and merge, record checks from the clean merged commit, then complete
the issue without marking user acceptance.

## Review outcome, 2026-10-25

The [simplification report] records one worthwhile test-harness cleanup:
consolidate four loopback HTTP server lifecycles and remove the unused `view`
clock override. Its unfiled draft names the existing preservation tests and
acceptance conditions. The report explains why compatibility fields, ordering
state, layer validation and the existing shared phone/watch tools remain.
No production or test changes were made, and no follow-up issues were filed.

Before merge, the report check passed: recorded baseline, required sections,
19 relative links and their anchors, source citation ranges at that baseline,
existing named tests, 19 argument-free `view` calls, and unchanged production
and test files. Manual review confirmed the four server lifetimes, cleanup
order and issue overlap. `git diff --check` passed. These bounded document
checks needed no heavy command; the offline suite, Ruff and ty will be
recorded at the merged commit with the memory guard.

[simplification report]: ../reviews/2026-10-25-simplification-review.md

## Merged verification, 2026-10-25

The shared `main` fast-forwarded from `a1a8cc676daaae2f7a78be13fbccf5c715b42243` to
`326b7dd0e38e3c1e59f2bd9ef39626e44a9fbe11`. The sole delivery commit is
`326b7dd0e38e3c1e59f2bd9ef39626e44a9fbe11`; the feature branch and worktree are retained.
The clean task checkout stayed at the merged commit throughout recording.
No commit intervened between the merge and completion evidence preparation.

The [check receipt] records four passing checks at that merged commit:

- **Report:** `git diff --check` and the embedded Python document check passed.
  Verified baseline, sections, 19 links and anchors, baseline citation bounds,
  named existing tests, all 19 `view` calls, and unchanged application/tests.
  Manual reading confirmed F1's callers, cleanup order and open-issue comparison.
- **Unit:** `command -v node` and `command -v cc` succeeded, then
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` passed
  all 106 tests in 14.009 seconds, with no skips. The suite's provider-access
  guard was active, including its narrowly permitted synthetic host drivers.
- **Lint:** `ruff check .` passed.
- **Types:** `ty check` passed.

No formatting correction was required. This repository has no dependency
lockfile or editable local package dependencies; the checks use the standard
library and installed tools, so dependency declarations are `{}`.
No service restart, live provider request, implementation change or issue
filing occurred. The report's draft remains for the steward; no owner decision
is needed.

## Memory reports for recorded checks

Each row names a separate recorder invocation, run sequentially from the clean
merged checkout with a 240-second timeout and process-group cleanup:

```bash
uv run "$EVIDENCE_RECORDER" record "$DECLARATION" 'pebble-quota [27]' <check-id>
```

The [check receipt] contains the exact recorder inputs and check commands.
Admission required 2048 MiB available; monitoring every 0.1 seconds would stop
at less than 1024 MiB or swap growth above 512 MiB. All commands completed;
none needed the 1536 MiB fallback. Memory values are MiB and times are seconds.

| Check ID | Outcome | Wait | Admission | Final | Starting swap | Swap growth | Elapsed | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `report` | started at once | 0.00 | 57378.7 | 57362.8 | 0.2 | 0.0 | 0.20 | exit 0 |
| `unittest` | started at once | 0.00 | 57364.1 | 57411.7 | 0.2 | 0.0 | 14.28 | exit 0 |
| `ruff` | started at once | 0.00 | 57419.5 | 57411.7 | 0.2 | 0.0 | 0.10 | exit 0 |
| `ty` | started at once | 0.00 | 57411.4 | 57383.6 | 0.2 | 0.0 | 0.30 | exit 0 |

[check receipt]: 27-review-pebble-quota-s-changes-since-the-10-22-architecture-review-for-.evidence.json
