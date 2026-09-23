# Issue tracking for Pebble Quota

Rules for TASKS.md usage are at the bottom of the file.

## Ordered backlog

- [1] Fix Codex 1% showing as 100%

## In progress


## Completed

- [*] Settings page for endpoint + token (survive reinstalls)

[*]: TASKS.md
[1]: docs/tasks/1-fix-codex-one-percent.md

---

## Rules

Here are the rules for TASKS.md usage:

### TASKS.md maintenance sessions

- Each backlog item must be prefixed with either
  - a numbered reference-style link (e.g. `[1]`) to a description file, or
  - `[*]` to indicate no description file is needed for a simple task.
- Link references are listed between `## Completed` and `## Rules`.
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
- When you move an issue to a different section, move its lines without
  a change. Keep the prefix, the bullet text and the line wrapping the same.
  Git can then see the move, and concurrent moves do not cause a conflict.

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
- Move the issue to `Completed` in TASKS.md and commit.
