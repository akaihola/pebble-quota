Steward issue, 2026-10-21 01:30. Goal: agentic-leverage (pebble-quota, the quota source, is a tier 1 project in `<steward-vault>/Goals.md`). Estimated 2 h.

[The security review](../reviews/2026-10-21-security-review.md) ([15]) found ten problems. This issue fixes the ones in the collector and the watch-face build that need no decision, no release and no credential:

- **F1, step 2 only:** build the watch face so that waf can't record secrets in its lock file: run `pebble build` and `pebble clean` with a minimal environment.
- **F2:** back off after a startup failure, including when the snapshot can't be written, instead of polling the providers every few seconds.
- **F4:** don't send the Claude or Home Assistant token on a redirect to another host, or from HTTPS to HTTP.
- **F7:** start the Codex subprocess with only the environment it needs.
- **F8:** add a test guard that fails any test that would reach a real provider or real credentials.
- **F9:** write snapshots with private permissions whatever the umask, through a private temporary file.
- **F10:** keep exception text out of the 503 status line; log it instead.

Each finding's section in the review gives the evidence and a drafted fix. Follow it unless the code shows a simpler one.

Not in scope: F1's other steps (deleting the lock files, replacing the keys and pruning history are Antti's), F3 (a Claude cooldown shared with kandev-pacer needs a design), F5 (the release workflow; checking it needs a GitHub Actions run) and F6 (already [6]).

## Constraints and acceptance

- Never open, print or use a credential file or a real token. Tests use fakes only; make no provider calls.
- Don't restart the collector service; the steward does that after the merge.
- The collector's tests pass, with a new test for each fixed finding. F1: if the Pebble SDK isn't installed here, show the Makefile change works with a test or a dry run, and say so.
- Memory: before each command, wait up to 10 minutes for `MemAvailable` of at least 2 GiB; if it doesn't come, start the command anyway when at least 1.5 GiB is available. Stop a running command when `MemAvailable` falls below 1 GiB or swap grows by more than 512 MiB. Run one heavy command at a time.
- Under each finding this issue fixes, the review gains one line: "Fixed by [N]", with this issue's number.

## Implementation plan

- Bind before starting the refresh thread. Retain collected state in memory,
  record provider attempt times before calls, and honour them after restarts.
- Refuse authenticated provider redirects and allowlist the Codex environment.
- Publish snapshots through unique private temporary files; log HTTP failures
  and return a fixed 503 response.
- Guard tests against live networking, subprocesses and credentials; add fake
  regression checks for every scoped finding and the build environment.
- Run the collector suite, review the diff, merge into main, and complete this
  issue pending acceptance. Leave the running service untouched.
