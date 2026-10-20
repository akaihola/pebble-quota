Steward issue, 2026-10-20 23:20. Goal: agentic-leverage (pebble-quota is tier 1 on [the goals page](http://hopeli/my-knowledge/pages/Goals.md?f)). Labelled `security` (security reviews stay on Claude, steward decision D68). Estimated 1 h.

pebble-quota's collector reads the Claude and Codex usage endpoints with Antti's subscription credentials and writes the `latest.json` that the pacer and every steward run read; the watch face shows it. It is the quota source for the whole pacing setup, and it has never had a security review ([5] checked an architecture review's plan).

## Work

1. Use the `security-review` skill over `collector/`, `watchface/`, `spikes/`, `tests/` and any CI files: how provider tokens are found, refreshed and held; whether a token, an authorization header or a raw response can reach `latest.json`, a log, a cache or an error message; file permissions of what it writes; which hosts it calls and whether any host comes from input; what the watch face side exposes and to whom; and whether its retry behaviour on HTTP 429 ([2]) could get the account rate-limited or flagged.
2. Search the history for secrets (`git log -p`): name the file and commit, never the value.
3. Write the report to `docs/reviews/2026-10-21-security-review.md`: findings ranked by impact and likelihood, each with file and line evidence and a drafted issue (title, work, acceptance) for each fix worth making. Link paths as relative links. Don't fix anything in this issue.
4. A live credential in the tree or history is urgent: say so first in your completion message, with its location only.

## Acceptance

- The report exists, covers every area in step 1 or says why it was skipped, and drafts an issue for each finding worth fixing.
- No secret value appears in the report, the commit or the thread.
- Read-only: no code change, credential use, call to a provider, push or service restart. Don't read credential files; the code tells you how they're used.

Host memory: hopeli is small and shared with other paced runs and Antti's sessions. Before a heavy command (a full test suite, a scan over the whole history), wait up to 10 minutes for 2 GiB `MemAvailable`; start at 1.5 GiB or more; stop and report below 1 GiB or on 512 MiB of swap growth since the command started. Stream large inputs instead of loading them whole.
