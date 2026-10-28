# Issue tracking for Pebble Quota

Rules for TASKS.md usage are at the bottom of the file.

## Unverified proposals

- [12] Document recoverable operation and reconcile build release assumptions
    - Depends on: [6], [7], [8], [9], [10], [11], [13], [14]

  <!-- hai:{"id":"simple-ad8ce943-0ba8-4801-95c6-2ecbabd61806","labels":["steward"],"createdAt":"2026-10-19T12:35:46.689Z","updatedAt":"2026-10-19T12:35:47.652Z"} -->

- [7] Gate releases on collector and phone behavior checks
  <!-- hai:{"id":"simple-0973cf3d-1685-468a-b2fe-aa6a52710543","labels":["steward"],"createdAt":"2026-10-19T12:35:35.717Z","updatedAt":"2026-10-19T12:35:35.717Z"} -->

- [6] Remove token URL transport and make settings recoverable
  <!-- hai:{"id":"simple-f5d94773-9467-431d-b527-2947873cdf46","labels":["steward"],"createdAt":"2026-10-19T12:35:35.429Z","updatedAt":"2026-10-19T12:35:35.429Z"} -->

## Ordered backlog

## Scheduled

## In Progress

- [~] [31] Log each Claude quota request's outcome so the rising 429 rate can be
  explained
      <!-- hai:{"id":"simple-d2846a48-0c64-4bde-8739-570cb863adbf","labels":["steward"],"createdAt":"2026-10-28T08:33:06.507Z","updatedAt":"2026-10-28T08:33:38.361Z"} -->

## Completed / Accepted

- [x] [25] Bundle the watchface settings page so it opens when the saved endpoint is
  down
      <!-- hai:{"id":"simple-fb1302d2-2afc-4abf-a98e-9a70e02deaa7","createdAt":"2026-10-23T19:04:15.185Z","updatedAt":"2026-10-27T06:31:21.159Z"} -->

- [ ] [30] Include Claude reset grants in quota snapshots
      <!-- hai:{"id":"simple-d0e422c9-7c3f-4d9a-b566-b0117c922964","createdAt":"2026-10-26T16:49:22.746Z","updatedAt":"2026-10-26T17:13:14.698Z"} -->

- [x] [29] Check pebble-quota's documents against the ten source changes since the
  10-22 docs review
      <!-- hai:{"id":"simple-01984467-4ebe-4ac4-bca6-f25d27f9ab34","labels":["steward","review"],"createdAt":"2026-10-24T23:50:27.223Z","updatedAt":"2026-10-25T00:14:46.375Z"} -->

- [x] [28] Share one loopback HTTP server helper across pebble-quota's tests
      <!-- hai:{"id":"simple-0bb6aca7-46a4-4c35-8174-69d3d6348f30","labels":["steward"],"createdAt":"2026-10-24T21:21:39.661Z","updatedAt":"2026-10-24T22:07:04.534Z"} -->

- [x] [27] Review pebble-quota's changes since the 10-22 architecture review for
  simplifications that keep behaviour
      <!-- hai:{"id":"simple-ecddbf13-895a-45b6-8a2f-c0d7d6dc6b1b","labels":["steward","review"],"createdAt":"2026-10-24T20:56:25.562Z","updatedAt":"2026-10-24T21:20:06.717Z"} -->

- [x] [14] Prevent older phone responses from overwriting newer settings or data
      <!-- hai:{"id":"simple-07285625-bd27-4eb2-8747-624e02681c4a","labels":["steward"],"createdAt":"2026-10-19T12:35:47.291Z","updatedAt":"2026-10-24T10:44:23.187Z"} -->

- [x] [26] Reject zero-byte watch strings before replacing rows
      <!-- hai:{"id":"simple-1446533a-f439-4760-b6ea-340b8b48b273","labels":["steward"],"createdAt":"2026-10-24T08:02:54.573Z","updatedAt":"2026-10-24T09:14:43.294Z"} -->

- [x] [11] Enforce the five-row collector phone and watch contract
    - Depends on: [8], [9]

      <!-- hai:{"id":"simple-4f4aa9f4-cf9c-4daf-a47b-240e65d9f106","labels":["steward"],"createdAt":"2026-10-19T12:35:36.920Z","updatedAt":"2026-10-24T09:47:58.493Z"} -->

- [x] [9] Carry freshness and failure status through to watch rendering
    - Depends on: [8]

      <!-- hai:{"id":"simple-f4553c58-87ef-4de4-b8db-1feff4b43833","labels":["steward"],"createdAt":"2026-10-19T12:35:36.286Z","updatedAt":"2026-10-24T08:01:47.986Z"} -->

- [x] [24] Remove unused collector helper generality
      <!-- hai:{"id":"simple-446bba0e-2d7a-4660-b462-7362295c7112","labels":["steward"],"createdAt":"2026-10-22T05:11:43.566Z","updatedAt":"2026-10-22T07:51:17.588Z"} -->

- [x] [23] Isolate the unavailable-snapshot merge
      <!-- hai:{"id":"simple-fa638f7f-2f94-4695-8677-8a989fa2da47","labels":["steward"],"createdAt":"2026-10-22T04:21:13.386Z","updatedAt":"2026-10-22T07:51:18.354Z"} -->

- [x] [22] Separate Codex result decoding from RPC
      <!-- hai:{"id":"simple-0c61a35c-ed10-43a8-ba83-09adad3b0348","labels":["steward"],"createdAt":"2026-10-22T04:21:11.751Z","updatedAt":"2026-10-22T07:51:19.360Z"} -->

- [x] [21] Use one compact payload decision for HTTP
      <!-- hai:{"id":"simple-6988dc7b-6270-4019-b391-03a6b66820f4","labels":["steward"],"createdAt":"2026-10-22T04:21:10.465Z","updatedAt":"2026-10-22T07:51:20.356Z"} -->

- [x] [20] Review pebble-quota's architecture for deep modules and over-engineering,
  and draft the fixes
      <!-- hai:{"id":"simple-5385fc70-974c-4eb4-bcd4-deaa7ad0b266","labels":["steward","review"],"createdAt":"2026-10-22T03:30:52.951Z","updatedAt":"2026-10-22T07:51:21.956Z"} -->

- [x] [19] Fix the seven Ruff and four ty findings and document both checks
      <!-- hai:{"id":"simple-3da495ef-c4ef-4533-baf5-c2cb4a3ffdb7","labels":["steward"],"createdAt":"2026-10-22T02:21:58.886Z","updatedAt":"2026-10-22T07:51:22.855Z"} -->

- [x] [18] Check pebble-quota's documents, docstrings and comments against current
  main
      <!-- hai:{"id":"simple-c22eff43-a865-4beb-9131-952fb456dd6f","labels":["steward","review"],"createdAt":"2026-10-22T01:31:09.461Z","updatedAt":"2026-10-22T07:51:23.656Z"} -->

- [x] [10] Report Codex RPC failures and reap the subprocess reliably
    - Depends on: [8]

      <!-- hai:{"id":"simple-1be37a59-fc45-417e-80e9-7f772086d4ef","labels":["steward"],"createdAt":"2026-10-19T12:35:36.626Z","updatedAt":"2026-10-22T07:51:24.388Z"} -->

- [x] [8] Validate windows and loaded snapshots before publication
      <!-- hai:{"id":"simple-ae2c788e-4c9e-4efd-841c-ee8f41766c5f","labels":["steward"],"createdAt":"2026-10-19T12:35:36.007Z","updatedAt":"2026-10-22T07:51:25.081Z"} -->

- [x] [17] Find what Claude's usage endpoint rate-limits on, from public sources and
  our own records
      <!-- hai:{"id":"simple-59034efe-5f31-4cbc-9291-ebfe54b0ab24","labels":["steward"],"createdAt":"2026-10-21T11:21:17.476Z","updatedAt":"2026-10-21T21:54:08.968Z"} -->

- [ ] [16] Fix the collector and build findings of the 2026-10-21 security review
      <!-- hai:{"id":"simple-fbb27a76-39b2-4c99-9ed9-428c1553858c","labels":["steward"],"createdAt":"2026-10-20T22:25:33.272Z","updatedAt":"2026-10-20T22:31:14.776Z"} -->

- [x] [15] Security scan of pebble-quota: provider tokens, outputs and history
      <!-- hai:{"id":"simple-71337a70-182d-486f-9f51-1fd788aba3af","labels":["steward","security"],"createdAt":"2026-10-20T20:10:50.486Z","updatedAt":"2026-10-21T05:18:31.763Z"} -->

- [x] [13] Make temperature units and entity age explicit
      <!-- hai:{"id":"simple-0df495bc-7407-4aec-a21b-301ab4b35cde","labels":["steward"],"createdAt":"2026-10-19T12:35:46.982Z","updatedAt":"2026-10-21T05:18:34.863Z"} -->

- [x] [5] Check the 2026-09-19 architecture review's remediation plan against the
  code and draft what remains
      <!-- hai:{"id":"simple-9769a664-fbb2-4433-867c-5e4a0a5f5ae6","labels":["steward","review"],"createdAt":"2026-10-19T11:13:08.369Z","updatedAt":"2026-10-19T14:05:48.956Z"} -->

- [x] [4] Gather acceptance evidence for the 2 review-queue items
      <!-- hai:{"id":"simple-0ffccc90-511b-4832-bb81-534f3491d36f","labels":["steward"],"createdAt":"2026-10-17T20:09:27.170Z","updatedAt":"2026-10-21T17:12:38.072Z"} -->

- [x] [3] Fix Claude 1% showing as 100%
      <!-- hai:{"id":"simple-d4d7e094-0d83-45fe-accf-7bedf7055f10","labels":["steward"],"createdAt":"2026-10-17T20:09:20.159Z","updatedAt":"2026-10-21T17:12:38.894Z"} -->

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

<!-- hai:reserved-numbers:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31 -->

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

[16]: docs/tasks/16-fix-the-collector-and-build-findings-of-the-2026-10-21-security-review.md

[17]: docs/tasks/17-find-what-claude-s-usage-endpoint-rate-limits-on-from-public-sources-a.md

[18]: docs/tasks/18-check-pebble-quota-s-documents-docstrings-and-comments-against-current.md

[19]: docs/tasks/19-fix-the-seven-ruff-and-four-ty-findings-and-document-both-checks.md

[20]: docs/tasks/20-review-pebble-quota-s-architecture-for-deep-modules-and-over-engineeri.md

[21]: docs/tasks/21-use-one-compact-payload-decision-for-http.md

[22]: docs/tasks/22-separate-codex-result-decoding-from-rpc.md

[23]: docs/tasks/23-isolate-the-unavailable-snapshot-merge.md

[24]: docs/tasks/24-remove-unused-collector-helper-generality.md

[25]: docs/tasks/25-bundle-the-watchface-settings-page-so-it-opens-when-the-saved-endpoint.md

[26]: docs/tasks/26-reject-zero-byte-watch-strings-before-replacing-rows.md

[27]: docs/tasks/27-review-pebble-quota-s-changes-since-the-10-22-architecture-review-for-.md

[28]: docs/tasks/28-share-one-loopback-http-server-helper-across-pebble-quota-s-tests.md

[29]: docs/tasks/29-check-pebble-quota-s-documents-against-the-ten-source-changes-since-th.md

[30]: docs/tasks/30-include-claude-reset-grants-in-quota-snapshots.md

[31]: docs/tasks/31-log-each-claude-quota-request-s-outcome-so-the-rising-429-rate-can-be-.md

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

`## Ordered backlog` and `## Scheduled` are the pacer's launch queue.
An agent or person doing the work itself must create or move the issue straight
to `## In Progress` on `main`, commit that change, then create the worktree branch
from there. `## Scheduled` is only for issues the heartbeat hands to the pacer.

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
