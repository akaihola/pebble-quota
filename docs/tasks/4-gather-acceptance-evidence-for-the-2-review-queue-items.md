# Gather acceptance evidence for the 2 review-queue items

Steward issue, 2026-10-17 (decisions D7, D10 and D37 in
`/home/agent/my-knowledge/agents/steward/decisions.md`). It takes over
pebble-quota's part of vault [17] and [20]. The vault's tracker is blocked, so
this check runs here, in the repository it checks. The verdicts feed the
steward's next digest, so that Antti can accept or reject these items with less
checking of his own.

## Items

These `- [ ]` items under `## Completed / Accepted`:

- [2], the HTTP 429 back-off, with Hai timestamps.
- The `[*]` watch face settings page for endpoint and token, a legacy bullet.

Items whose Hai metadata has no `updatedAt` (it starts with 1970 in `hai-tasks
read`) are legacy bullets that predate Hai timestamps. Judge them against
today's `main`: find the commits that delivered each one (`git log -S`,
`--grep`, its description under `docs/tasks/`) and check that the behaviour
still exists. An item superseded by later work is "would accept" only when the
later work covers its request; name the issue that superseded it.

## Work

Run `python3 -m unittest discover -s tests -v` once on current `main`. The
watch face has no automated test: judge the settings page from the code and say
so. Check criterion 3 with `git revert --no-commit` of an item's merge commits
in a temporary worktree (`git worktree add --detach "$TMPDIR/revert-check"
main`, removed afterwards); conflicts only in `TASKS.md` and `docs/tasks/`
don't count.

For each item, record one line: issue, a one-line outcome, the evidence
(commits, files, test command with pass and fail counts) and a verdict under
`/home/agent/my-knowledge/agents/steward/acceptance-policy.md`:

- **would accept:** all four criteria hold; give the revert command;
- **left to Antti:** name the criterion or the "Always left to Antti" class;
- **not done:** say what is missing.

## Deliverable

A section `## Evidence, YYYY-MM-DD` in this description file, with the lines
grouped by verdict and the counts per verdict at the end.

## Ground rules

- Change no other issue's state or text, and never change `[ ]` to `[x]`: only
  Antti accepts.
- Don't push, deploy or restart services, and don't touch the vault or the
  running pacer.

## Acceptance

- Every listed item has a line with evidence and a verdict.
- Nothing outside this file and the issue's own tracker moves changed.

## Plan

1. Read the shadow acceptance policy and identify the delivery commits for
   [2] and the legacy settings item on current main.
2. Run the full unittest suite once on main and inspect both implementations,
   including settings persistence and reader compatibility.
3. Attempt each delivery revert independently in a disposable detached main
   worktree. Separate tracker-only conflicts from implementation conflicts.
4. Record one evidence line per item, grouped by policy verdict with totals.
   Merge the documentation locally and complete [4] pending Antti's acceptance.

## Evidence, 2026-10-17

Reviewed main `5825d304335613dd7acfdeafeeb46f4032568616`, with application
code unchanged from `c6e5fe8`. Ran `python3 -m unittest discover -s tests -v`
once from the main worktree: 35 passed, 0 failed, 0 errors, 0 skipped.
Policy is shadow mode. Neither listed item is superseded on today's main.
The newer [3] percentage fix preserves [2]'s backoff behavior.

### Left to Antti

- [2] HTTP 429 backoff retains the last Claude windows with stale age/error, persists cooldown across refreshes, honors useful Retry-After headers or exponential 600–3600-second delays, and recovers without interrupting Codex or temperature; evidence: delivery `658613c`, completion `0c947b5`, `collector/pebble_quota.py` functions `claude_retry_delay`, `collect_all`, `refresh_snapshot`, `tests/test_pebble_quota.py` class `ClaudeBackoffTests`, and the findings/validation in `docs/tasks/2-back-off-on-http-429-from-claude-s-usage-endpoint-and-keep-the-last-re.md`; `python3 -m unittest discover -s tests -v`: 35 passed, 0 failed, including all seven backoff tests and retained-window reader compatibility; criteria 1's explicit acceptance tests, 2 and 4 hold, and criterion 3 holds with `git revert --no-commit 658613c`, which removes all backoff code/tests and conflicts only in `TASKS.md`; **left to Antti**, the policy's "anything the worker reported as blocked, partial or unverified" class applies because work step 1's throttle key remains explicitly unverified in the worker's findings, despite the completed functional acceptance checks.
- [*] Settings page for endpoint + token exists and saves phone-side settings for subsequent requests, while survival across reinstalls remains unverified; evidence: legacy Hai updatedAt `1970-01-01T00:00:00.000Z`, delivery `91a4ac9`, follow-up `535ef7b` enabling the configuration gear, `watchface/package.json` configurable capability, `watchface/src/pkjs/index.js` functions `setting`, `configUrl` and showConfiguration/webviewclosed handlers, `collector/pebble_quota.py` CONFIG_PAGE and `/config` handler, plus `watchface/README.md`; `python3 -m unittest discover -s tests -v`: 35 passed, 0 failed, including server-side config-page/auth tests, but no automated watch-face settings or reinstall test, so the phone flow is judged from code only; criterion 3 holds with `git revert --no-commit 535ef7b` then `git revert --no-commit 91a4ac9`, removing configuration capability, HTML/route and JS handlers with only `TASKS.md` conflicts; criteria 2 and 4 hold, but criterion 1's reinstall claim needs device evidence, also noted in `docs/2026-09-19-architecture-review-and-remediation-plan.md`; **left to Antti**, the "Secrets or credentials" and "unverified" classes apply, and the existing token is passed through the settings URL query.

Both deliveries are ordinary single-parent commits on main, rather than merge
commits, so the revert checks target those delivery commits directly. Each
item was checked independently in a disposable detached worktree created with
`git worktree add --detach "$TMPDIR/revert-check" main`. For the two settings
reverts, kept main's `TASKS.md` after each tracker-only conflict, staged it,
and ran `git revert --quit` before the next `--no-commit` command. The combined
staged diff removed all settings delivery code without a code conflict or a
change to HEAD. All temporary worktrees were removed afterwards. These are
source reversals, not a deployment or a deletion of saved readings/settings.

Counts: **would accept: 0; left to Antti: 2; not done: 0.**

No acceptance boxes changed. The vault was read only; no credentials were
read, no live provider requests were made, and no push, deployment, service
restart or pacer change was performed. Only this description and [4]'s own
tracker moves changed.
