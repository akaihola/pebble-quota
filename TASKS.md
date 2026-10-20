# Issue tracking for Pebble Quota

Rules for TASKS.md usage are at the bottom of the file.

## Unverified proposals

- [14] Prevent older phone responses from overwriting newer settings or data
    - Depends on: [7]

  <!-- hai:{"id":"simple-07285625-bd27-4eb2-8747-624e02681c4a","labels":["steward"],"createdAt":"2026-10-19T12:35:47.291Z","updatedAt":"2026-10-19T12:35:47.291Z"} -->

- [12] Document recoverable operation and reconcile build release assumptions
    - Depends on: [6], [7], [8], [9], [10], [11], [13], [14]

  <!-- hai:{"id":"simple-ad8ce943-0ba8-4801-95c6-2ecbabd61806","labels":["steward"],"createdAt":"2026-10-19T12:35:46.689Z","updatedAt":"2026-10-19T12:35:47.652Z"} -->

- [11] Enforce the five-row collector phone and watch contract
    - Depends on: [8], [9]

  <!-- hai:{"id":"simple-4f4aa9f4-cf9c-4daf-a47b-240e65d9f106","labels":["steward"],"createdAt":"2026-10-19T12:35:36.920Z","updatedAt":"2026-10-19T12:35:36.920Z"} -->

- [10] Report Codex RPC failures and reap the subprocess reliably
    - Depends on: [8]

  <!-- hai:{"id":"simple-1be37a59-fc45-417e-80e9-7f772086d4ef","labels":["steward"],"createdAt":"2026-10-19T12:35:36.626Z","updatedAt":"2026-10-19T12:35:36.626Z"} -->

- [9] Carry freshness and failure status through to watch rendering
    - Depends on: [8]

  <!-- hai:{"id":"simple-f4553c58-87ef-4de4-b8db-1feff4b43833","labels":["steward"],"createdAt":"2026-10-19T12:35:36.286Z","updatedAt":"2026-10-19T12:35:36.286Z"} -->

- [8] Validate windows and loaded snapshots before publication
    - Depends on: [7]

  <!-- hai:{"id":"simple-ae2c788e-4c9e-4efd-841c-ee8f41766c5f","labels":["steward"],"createdAt":"2026-10-19T12:35:36.007Z","updatedAt":"2026-10-19T12:35:36.007Z"} -->

- [7] Gate releases on collector and phone behavior checks
  <!-- hai:{"id":"simple-0973cf3d-1685-468a-b2fe-aa6a52710543","labels":["steward"],"createdAt":"2026-10-19T12:35:35.717Z","updatedAt":"2026-10-19T12:35:35.717Z"} -->

- [6] Remove token URL transport and make settings recoverable
  <!-- hai:{"id":"simple-f5d94773-9467-431d-b527-2947873cdf46","labels":["steward"],"createdAt":"2026-10-19T12:35:35.429Z","updatedAt":"2026-10-19T12:35:35.429Z"} -->

## Ordered backlog

## Scheduled

## In Progress

- [~] [15] Security scan of pebble-quota: provider tokens, outputs and history
      <!-- hai:{"id":"simple-71337a70-182d-486f-9f51-1fd788aba3af","labels":["steward","security"],"createdAt":"2026-10-20T20:10:50.486Z","updatedAt":"2026-10-20T20:45:05.070Z"} -->

## Completed / Accepted

- [ ] [13] Make temperature units and entity age explicit
      <!-- hai:{"id":"simple-0df495bc-7407-4aec-a21b-301ab4b35cde","labels":["steward"],"createdAt":"2026-10-19T12:35:46.982Z","updatedAt":"2026-10-19T16:02:05.181Z"} -->

- [x] [5] Check the 2026-09-19 architecture review's remediation plan against the
  code and draft what remains
      <!-- hai:{"id":"simple-9769a664-fbb2-4433-867c-5e4a0a5f5ae6","labels":["steward","review"],"createdAt":"2026-10-19T11:13:08.369Z","updatedAt":"2026-10-19T14:05:48.956Z"} -->

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

<!-- hai:reserved-numbers:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 -->

[3]: docs/tasks/3-fix-claude-1-showing-as-100.md

[4]: docs/tasks/4-gather-acceptance-evidence-for-the-2-review-queue-items.md

[5]: docs/tasks/5-check-the-2026-09-19-architecture-review-s-remediation-plan-against-th.md

[6]: docs/tasks/6-remove-token-url-transport-and-make-settings-recoverable.md

[7]: docs/tasks/7-gate-releases-on-collector-and-phone-behavior-checks.md

[8]: docs/tasks/8-validate-windows-and-loaded-snapshots-before-publication.md

[9]: docs/tasks/9-carry-freshness-and-failure-status-through-to-watch-rendering.md

[10]: docs/tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md

[11]: docs/tasks/11-enforce-the-five-row-collector-phone-and-watch-contract.md

[12]: docs/tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md

[13]: docs/tasks/13-make-temperature-units-and-entity-age-explicit.md

[14]: docs/tasks/14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.md

[15]: docs/tasks/15-security-scan-of-pebble-quota-provider-tokens-outputs-and-history.md

## Rules

Here are the rules for TASKS.md usage:

### TASKS.md maintenance sessions

- In `## Completed / Accepted`, `- [ ] [N] summary` or `- [ ] [*] summary`
  means completed work awaiting user acceptance. `- [x] [N] summary` or
  `- [x] [*] summary` means the user has accepted it. Only user acceptance, or the steward's under its
  acceptance policy, changes `[ ]` to `[x]`; completion, tests and deployment do not.
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
- Merge the rebased branch on `main`.
- Keep the worktree and branch after merging. Remove them only when the user
  explicitly requests it.
- Move the issue to `Completed / Accepted` in TASKS.md with `[ ]`,
  pending user acceptance, and commit.
