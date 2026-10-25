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


## Implementation and review

The [documentation recheck] inventories all ten source commits from `505c04b`
through `b9e6118`, with behavior, payload, setting, file and message effects.
Read the three required documents and the [watchface guide] in full. Corrected
pass-time wording, the Claude-only example, temperature bounds, zero-byte
string rejection and stale-state claims. Linked the existing phone-ordering
policy and removed repeated five-line/freshness explanations. Updated the
review link and test Python requirement; kept agent instructions unchanged.

The three guides are shorter overall. The report ties every change to source
or a commit and ends with two unfiled steward candidates: temperature boundary
consistency and Codex child-shell portability. These are future code work, not
unfinished documentation fixes. Earlier reviews, the dated architecture plan,
other task files, production code and tests are unchanged. No formatting-only
exception was needed. No service, credential, live configuration or device was
touched, and no real provider request or watch build was run.

## Validation before merge

- **Offline suite:** `python3 -m unittest discover -s tests -v` — exit 0;
  106 tests, no failures/errors/skips. Node and the host C compiler were present;
  provider, credential and subprocess guards stayed enabled.
- **Ruff:** `ruff check .` — exit 0, no findings.
- **ty:** `ty check` — exit 0, no findings.
- **Documentation:** `python3 "$DOCS_CHECK"` — exit 0; six documents and 59
  existing local links/anchors checked, including the task/review. Checked the
  ten-commit inventory, the example against `compact_watch`, allowed file scope,
  historical preservation and whitespace. The guide's existing generated-bundle
  link is explicitly recognized as a build output. The external check script
  is recorded by SHA-256 in the receipt; no test file was added to the repository.
- **Manual review:** all ten source changes matched against current code and
  related tests; inspected the final guide diff and the recheck's source
  attributions. The agent instructions add no check beyond the tracker workflow;
  validation uses the entry point's three commands.

Environment: Python 3.14.7, Ruff 0.16.8, ty 0.0.84. No minimum-Python matrix or
installed-Codex compatibility check; both are outside this source-only review.

## Memory reports before merge

All guarded commands ran sequentially with timeouts and process-group cleanup.
`$DOCS_CHECK` denotes the external documentation-check script identified in the
receipt. Memory figures describe the host, not individual process usage.

- **source-history:** `git log --no-merges --reverse '--format=%h %s' --stat 418b500..main -- . ':!docs' ':!*.md'` — started at once; wait 0.0 s; MemAvailable admission/final 57676.1/57676.1 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 0.1 s; exit 0.
- **pre-offline-suite:** `python3 -m unittest discover -s tests -v` — started at once; wait 0.0 s; MemAvailable admission/final 57686.8/57671.2 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 14.38 s; exit 0.
- **pre-ruff:** `ruff check .` — started at once; wait 0.0 s; MemAvailable admission/final 57682.9/57675.3 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 0.1 s; exit 0.
- **pre-ty:** `ty check` — started at once; wait 0.0 s; MemAvailable admission/final 57675.3/57685.2 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 0.2 s; exit 0.
- **pre-docs:** `python3 "$DOCS_CHECK"` — started at once; wait 0.0 s; MemAvailable admission/final 57684.2/57671.4 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 0.1 s; exit 0.

- **pre-final-docs:** `python3 "$DOCS_CHECK"` — started at once; wait 0.0 s; MemAvailable admission/final 57700.9/57699.9 MiB; starting swap 0.5 MiB, growth 0.0 MiB; elapsed 0.1 s; exit 0.

[project entry point]: ../../README.md
[agent instructions]: ../../AGENTS.md
[collector reference]: ../collector.md
[documentation recheck]: ../reviews/2026-10-25-docs-recheck.md

[watchface guide]: ../../watchface/README.md
