# Issue tracking for Pebble Quota

Rules for TASKS.md usage are at the bottom of the file.

## Unverified proposals

## Ordered backlog

## Scheduled

## In Progress

## Completed / Accepted

- [ ] [4] Gather acceptance evidence for the 2 review-queue items
      <!-- hai:{"id":"simple-0ffccc90-511b-4832-bb81-534f3491d36f","labels":["steward"],"createdAt":"2026-10-17T20:09:27.170Z","updatedAt":"2026-10-17T20:23:38.964Z"} -->

- [ ] [3] Fix Claude 1% showing as 100%
      <!-- hai:{"id":"simple-d4d7e094-0d83-45fe-accf-7bedf7055f10","labels":["steward"],"createdAt":"2026-10-17T20:09:20.159Z","updatedAt":"2026-10-17T20:22:09.108Z"} -->

- [ ] [2] Back off on HTTP 429 from Claude's usage endpoint and keep the last
  reading
      <!-- hai:{"id":"simple-6ff28cdb-2526-474f-84cd-846a148f59e0","labels":["steward"],"createdAt":"2026-10-17T08:11:31.000Z","updatedAt":"2026-10-17T08:56:22.186Z"} -->

- [ ] [*] Settings page for endpoint + token (survive reinstalls)
- [x] [1] Fix Codex 1% showing as 100%
  <!-- hai:{"updatedAt":"2026-10-10T19:45:45.366Z"} -->

[*]: TASKS.md
[1]: docs/tasks/1-fix-codex-one-percent.md

---

[2]: docs/tasks/2-back-off-on-http-429-from-claude-s-usage-endpoint-and-keep-the-last-re.md

<!-- hai:reserved-numbers:1,2,3,4 -->

[3]: docs/tasks/3-fix-claude-1-showing-as-100.md

[4]: docs/tasks/4-gather-acceptance-evidence-for-the-2-review-queue-items.md

## Rules

Here are the rules for TASKS.md usage:

### TASKS.md maintenance sessions

- In `## Completed / Accepted`, `- [ ] [N] summary` or `- [ ] [*] summary`
  means completed work awaiting user acceptance. `- [x] [N] summary` or
  `- [x] [*] summary` means the user has accepted it. Only user acceptance
  changes `[ ]` to `[x]`; completion, tests and deployment do not.
- Move newly completed issues into `## Completed / Accepted` with `[ ]`.
- During the next maintenance run, remove only `[x]` issues from this section,
  plus their unused description files and reference-style links. Keep `[ ]`
  issues and any files or links still referenced by another issue.
- Each issue must retain either
  - a numbered reference-style link (e.g. `[1]`) to a description file, or
  - `[*]` to indicate no description file is needed for a simple task.
- Link references are listed between `## Completed / Accepted` and `## Rules`.
- Keep each issue in exactly one status section.
- Keep simple tasks inline with `[*]`. For longer tasks, keep a concise summary
  here and move requirements, rationale, examples, and acceptance criteria to
  `docs/tasks/<N-issue-description>.md`, preserving all substantive details.
- Reuse existing task numbers and description files. For a new description,
  use the first unused positive integer across this tracker and `docs/tasks/`,
  without zero-padding, and add its numbered reference-style link.
- Verify links and status changes against description files, repository history,
  and available task-tracker evidence before changing issue placement.

### Modifying issues

- Ensure dependencies between issues are correctly updated.
- State dependencies using
  - indented `- Depends on: [N]` bullets in TASKS.md, and
  - YAML frontmatter in description files.
- Ensure backlog order respects dependencies.
- When you move an issue, preserve its identifier, text and line wrapping.
  Change only the status checkbox when completion or user acceptance requires it.
  This keeps moves identifiable in Git and reduces avoidable conflicts.

### Workflow for new issue completion

- Pick the first backlog issue with no dependency to any uncompleted issue.
- Move it to `In progress` in `main` branch.
- Create or update, review and refine a plan in
  docs/tasks/<N-issue-description>.md in `main` (skip for `[*]` items).
- Commit description file (if any) and TASKS.md in `main`.
- Rebase the worktree feature branch on `main` before moving the issue, and keep
  it rebased afterwards.
- Implement the plan, and lint, test, review and refine the implementation in
  the worktree feature branch.
- Merge the rebased branch on `main`, and remove the worktree and branch.
- Move the issue to `Completed / Accepted` in TASKS.md with `[ ]`,
  pending user acceptance, and commit.
