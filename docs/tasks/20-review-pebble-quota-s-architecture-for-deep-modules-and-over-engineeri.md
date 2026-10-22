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

## Outcome and verification

The [architecture report] reviews local `main` at
`61ebe07c4ba9e377f14980ceee761dcd284e68d1`, after the start/plan commits and
worktree rebase. It has five ranked findings with code/line evidence, expected
maintenance benefits and five bounded draft issues. The first three are one
HTTP publication decision, a pure Codex result decoder and a pure unavailable
snapshot merge. The behavior-test gate is explicitly a refinement of the
existing proposal, not a new issue; helper deletion is lower priority.

Reviewed the entry/collector/watchface guides, historical reviews and existing
task criteria; traced production Python, phone JS, watch C, the offline suite
and build/release configuration. The historical spike has no production
dependency. The earlier September architecture review is acknowledged rather
than repeating this issue's premise that no review existed. Honey was loaded;
the requested deep-module vocabulary was applied directly because no
`codebase-design` skill was available in this session.

Drafts identify overlaps with all six Unverified proposals and distinguish
completed validation, RPC, temperature, security-fix and checker work from new
refactoring. No draft was filed or implemented. The report preserves current
retention asymmetry, retry checkpoints, write-failure memory state, protocol
and error behavior as explicit constraints. It records why provider/plugin,
cache, RPC, schema and rendering frameworks are unnecessary.

- **Tests:** `python3 -m unittest discover -s tests -v` passed all 66 tests in
  7.489 seconds, zero failures/errors/skips, Python 3.14.7. The existing live
  access guard was active; provider processes/responses were fixtures and HTTP
  servers were loopback-only. Existing security regressions ran as part of the
  unchanged suite; no additional vulnerability probes were made.
- **Static checks:** `ruff check .` (0.16.8), `ty check` (0.0.84), and
  `node --check watchface/src/pkjs/index.js` (Node 24.21.0) all exited 0.
  The temporary resource wrapper's initial edit hook caught one dictionary
  literal style issue; it was corrected before any guarded command ran.
- **Report checks:** relative reference targets, cited source line bounds,
  equality of cited source with the pinned main commit, five finding/draft
  pairs, the final Draft issues section, recommendation order and whitespace
  were checked. Manual review verified that every finding states what changes,
  each draft has work/acceptance and effort, and all six Unverified proposals
  have an explicit owner/overlap entry. Runtime and test files are unchanged.
- **Tracker checks:** canonical `hai-tasks read` confirms the existing issue ID
  and preserves all other issues; no proposal or acceptance checkbox was added.
  Tracker Rules specify no separate validator.
- **Limits:** no PBW build, emulator, physical phone/watch, live quota call,
  installed Codex compatibility check, service restart/deployment or hosted CI
  execution was performed. These are outside this report's acceptance. The
  drafts label their later verification needs, including hosted CI for D4 and
  device evidence for existing settings/rendering proposals. There are no
  unresolved report acceptance conditions or owner decisions.

## Memory-guarded commands

Commands ran one at a time, with a 300-second execution timeout, a process-group
cleanup and 0.1-second memory monitoring. Admission waits up to 600 seconds for
2,048 MiB, permits fallback only at 1,536 MiB, and stops below 1,024 MiB or above
512 MiB swap growth. All four commands started normally with zero wait; no
fallback, timeout or running stop occurred. Readings below are MiB; elapsed time
includes wrapper monitoring, not admission wait. Command output is excluded.

- **Inventory — `git ls-files`:** started at once; wait 0.00 s; admission
  MemAvailable 2528.48; final 2528.58; starting swap 2312.69; swap growth 0.00;
  elapsed 0.10 s; exit 0.
- **Suite — `python3 -m unittest discover -s tests -v`:** started at once;
  wait 0.00 s; admission MemAvailable 2950.37; final 2945.39; starting swap
  2372.39; swap growth 0.00; elapsed 7.80 s; exit 0.
- **Lint — `ruff check .`:** started at once; wait 0.00 s; admission
  MemAvailable 2883.84; final 2891.23; starting swap 2372.14; swap growth 0.00;
  elapsed 0.20 s; exit 0.
- **Types — `ty check`:** started at once; wait 0.00 s; admission MemAvailable
  2901.59; final 2908.24; starting swap 2372.14; swap growth 0.00;
  elapsed 1.21 s; exit 0.

## Merge and handoff

The required start move was committed immediately on canonical `main` as
`368d976`, leaving no uncommitted tracker changes. Plan commit `61ebe07` followed
on `main`; the retained feature worktree was rebased onto it before review.
Only the report and this task record are included in the implementation commit.
Merge and completion evidence will be recorded after the final checks.

The steward chooses which drafts to file/promote; no message or new thread is
needed. No owner action is required for this completed review. The branch and
worktree are retained, and acceptance stays unchecked for steward/user review.

[19]: 19-fix-the-seven-ruff-and-four-ty-findings-and-document-both-checks.md
[architecture report]: ../reviews/2026-10-22-architecture-review.md
