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
