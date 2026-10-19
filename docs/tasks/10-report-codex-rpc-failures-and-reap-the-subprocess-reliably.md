---
depends-on: [8]
---

# Report Codex RPC failures and reap the subprocess reliably

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

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
