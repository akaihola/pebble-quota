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
