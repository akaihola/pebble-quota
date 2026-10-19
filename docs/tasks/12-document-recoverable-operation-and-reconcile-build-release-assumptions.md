---
depends-on: [6, 7, 8, 9, 10, 11, 13, 14]
---

# Document recoverable operation and reconcile build release assumptions

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F8 / Step 8, lower-priority writer/HTTP/release/calendar items and
Step 1 historical spike cleanup. README only gained backoff semantics since review.

## Acceptance criteria

- Document complete top-level v/at/q/t and row schema including F code, five-row
  selection, failure/freshness policy, sample redacted payload, CLI defaults,
  collector vs phone cadence and correct origin/base /config URL.
- Supply a minimal service example or precise authoritative configuration reference:
  credential user/HOME, Codex PATH/version, working directory/absolute state path,
  permissions/logs, restart policy, loopback/private TLS boundary, token provisioning,
  rotation and recovery. Declare one writer; only add unique temporary files and a
  two-writer test if concurrent manual collection is intentionally supported.
- Reconcile SDK 4.17 README with CI 4.33.1 and Makefile SDKs/current. Mark the spike
  historical and point to production; retain its old evidence without maintaining
  a second collector. Commit calendar harness if promising continuing coverage,
  otherwise qualify the historical verification. Qualify reinstall persistence.
- Check real tags/release history before changing package 0.2.0 vs manifest 0.1.0;
  document interrupted-upload retry and prove it in a disposable mock/staging flow
  without publishing production. Do not assume version mismatch proves a failure.
- A reviewer can perform offline/mock startup, locate logs/state, rebuild PBW and
  follow credential/stale-data recovery. Auth/no-auth/error tests match docs.
  Authorized staging proxy checks cover both endpoints and loopback isolation;
  explicitly record unavailable operational evidence. No production deployment is
  authorized by this proposal. Keep previous collector/PBW and back up real config.
