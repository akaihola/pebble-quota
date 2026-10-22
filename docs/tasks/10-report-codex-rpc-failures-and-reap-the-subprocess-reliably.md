---
depends-on: [8]
---

# Report Codex RPC failures and reap the subprocess reliably

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Promoted by the steward, 2026-10-22 01:58 refill (D13). Goal: agentic-leverage (pebble-quota is tier 1 on the goals page). Checked on current `main` before promoting: `collect_codex()` still treats an RPC `error` reply to request 2 as an empty window set, and `proc.kill()` is not followed by a `wait()`. Estimated 1.5 h.

Constraints for this run: tests use fakes and fixtures only; never call an authenticated provider, print a credential, or restart the collector service (the steward restarts it after acceptance, D78). Memory: before each command, wait up to 10 minutes for `MemAvailable` of at least 2 GiB; if it doesn't come, start anyway at 1.5 GiB or more. Stop a running command when `MemAvailable` falls below 1 GiB or swap grows by more than 512 MiB. Run `python3 -m unittest discover -s tests -v` before merging. Handoff: a short outcome and the test result; put detail in this task record.

Review F6 / Step 6. collect_codex still accepts RPC errors as empty windows;
queue.Empty/EOF conceal causes and kill lacks a subsequent wait/pipe cleanup.

## Acceptance criteria

- Check initialize and rate-limit errors and result shapes; distinguish timeout,
  EOF, malformed JSON, notifications and legitimate no-window responses with
  actionable sanitized diagnostics. Preserve duration-based window labels.
- Every exit path terminates/kills as needed, reaps the child and closes pipes.
  Keep the small subprocess adapter; no RPC framework or provider plugin layer.
- Fake app-server tests cover success, intervening notifications, both RPC errors,
  EOF, no response, invalid JSON/results, empty windows and forced-kill cleanup.
  Do not invoke authenticated Codex in tests; other provider rows remain deliverable.
- Record the CLI version used for authorized compatibility verification in operations
  docs, or explicitly mark it unverified when only fakes were available.

## Implementation plan

- Validate initialize and rate-limit replies in the existing stdio adapter.
  Ignore notifications while retaining one overall response deadline. Expose
  fixed diagnostics for RPC failure, EOF, timeout, JSON and result errors.
- Preserve duration labels and usable sibling windows. Accept explicit empty
  window sets while rejecting malformed result containers.
- Terminate, escalate to kill when needed, wait, and close the pipes on every
  adapter exit. Exercise lifecycle and protocol paths with fake servers only.
- Run the required full unittest suite, review the diff, merge into main and
  complete the tracker pending acceptance. Leave compatibility explicitly
  unverified in operations documentation; no authenticated provider calls or
  service restart are authorized.

## Implementation and verification

- The existing subprocess adapter now validates the initialize handshake and
  rate-limit envelopes, ignores notifications without extending the deadline,
  and distinguishes RPC errors, timeout, EOF, invalid JSON, malformed responses,
  malformed results and pipe failures. Diagnostics contain only fixed strings.
- Explicit no-window responses keep an empty window map and report
  `Codex rate limits: no quota windows`; this survives snapshot normalization.
  Malformed windows cannot suppress valid siblings. Duration-based labels
  remain unchanged, including the 5h, 7d and arbitrary-minute labels.
- Cleanup terminates the subprocess, waits with a grace period, kills and waits
  again when necessary, joins the reader and closes both pipes. The subprocess
  environment explicitly sets Bash while preserving the credential allowlist.
- Generated Python app-server fixtures cover the handshake, intervening
  notifications, notifications without a reply, both RPC errors, EOF and timeout
  during either stage, malformed JSON/envelopes/results, empty windows, duration
  labels, write failure and SIGTERM-resistant children on success and failure.
  Each real fixture process is checked for reaping and closed pipes.
- The required full suite passed: **66 tests**, 7.292 seconds.
  The initial run had two new-test assertion errors (wrong compact payload key);
  corrected to the existing `q` contract. An intermediate run passed 65 tests.
  The last run adds the no-window snapshot diagnostic regression.
- `git diff --check` passed. Manual review covered the protocol state transitions,
  fixed diagnostic allowlist, sibling-window preservation and all cleanup paths.
- Optional Ruff and ty checks remain nonzero on both the base and this change:
  **22 Ruff and 12 ty diagnostics**, with identical diagnostic code/message
  multisets and no additions. Existing issues include executable/import/type
  style, broad exception handlers, server attribute typing and older test mocks.
  Early edit-hook failures were these existing findings; new test style warnings
  were corrected. The first comparison attempted an unsupported ty JSON format;
  it was rerun using concise output and a corrected comparison parser.
- CLI compatibility is explicitly **unverified** in the [operations guidance].
  Only fake servers were invoked; no authenticated provider, credential access,
  service restart or deployment was performed. The steward handles restart
  after acceptance. No owner decision or agent-owned implementation gap remains.
- Start state was committed on main as `176d6ff`; the plan was committed as
  `581faa8`. Completion remains unchecked pending steward/user acceptance.
  The feature branch and worktree are retained after merging.

## Memory guard record

All readings are MiB. The wrapper waits up to 600 seconds for 2048 MiB,
allows the 1536 MiB fallback, and monitors every 0.1 seconds while running.
It terminates the process group below 1024 MiB or above 512 MiB swap growth,
and bounds commands to 300 seconds. No command required fallback or stopping.
The paired readings are admission/final available memory and start/growth swap.
Exit codes below are command completion statuses, independent of test outcomes
reported above. Comparison wrapper exit 0 means the comparison completed;
individual Ruff/ty checks still exited 1 as described above.

| Command | Outcome; admission wait | Available | Swap | Elapsed | Exit |
| --- | --- | --- | --- | --- | --- |
| `python3 -m unittest discover -s tests -v` | started at once; 0.0 s | 2948 / 2903 | 2391 / 0 | 9.51 s | 1 |
| `python3 -m unittest discover -s tests -v` | started at once; 0.0 s | 3064 / 3082 | 2390 / 0 | 7.56 s | 0 |
| Baseline/current Ruff and ty comparison 1 | started at once; 0.0 s | 3095 / 3084 | 2390 / 0 | 0.2 s | 0 |
| Baseline/current Ruff and ty comparison 2 | started at once; 0.0 s | 3102 / 3052 | 2389 / 0 | 1.21 s | 0 |
| `python3 -m unittest discover -s tests -v` | started at once; 0.0 s | 3077 / 3066 | 2387 / 0 | 7.56 s | 0 |
| Baseline/current Ruff and ty comparison 3 | started at once; 0.0 s | 3083 / 3073 | 2386 / 0 | 1.11 s | 0 |

[operations guidance]: ../../README.md
