# Issue tracking for Pebble Quota

Rules for TASKS.md usage are at the bottom of the file.

## Ordered backlog

- [1] Fix Codex 1% showing as 100%
- [*] Settings page for endpoint + token (survive reinstalls)

## In progress


## Completed

[*]: TASKS.md
[1]: docs/tasks/1-fix-codex-one-percent.md
- [*] Settings page for endpoint + token (survive reinstalls)

---

## Rules

Here are the rules for TASKS.md usage:

### TASKS.md maintenance sessions

- Each backlog item must be prefixed with either
  - a numbered reference-style link (e.g. `[1]`) to a description file, or
  - `[*]` to indicate no description file is needed for a simple task.
- Link references are listed between `## Completed` and `## Rules`.
- If any issue is missing a link:
  - Create the first missing numbered description file in
    docs/tasks/<NNN-issue-description>.md and add the link

### Modifying issues

- Ensure dependencies between issues are correctly updated.
- State dependencies using
  - indented `- Depends on: [N]` bullets in TASKS.md, and
  - YAML frontmatter in description files.
- Ensure backlog order respects dependencies.

### Workflow for new issue completion

- Pick the first backlog issue with no dependency to any uncompleted issue.
- Move it to `In progress` in `main` branch.
- Create or update, review and refine a plan in
  docs/tasks/<N-issue-description>.md in `main` (skip for `[*]` items).
- Commit description file (if any) and TASKS.md in `main`.
- From now on, ensure worktree feature branch is always rebased on `main`.
- Implement the plan, and lint, test, review and refine the implementation in
  the worktree feature branch.
- Merge the rebased branch on `main`, and remove the worktree and branch.
- Move the issue to `Completed` in TASKS.md and commit.
