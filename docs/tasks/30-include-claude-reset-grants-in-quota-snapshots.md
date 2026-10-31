Request Claude reset grant metadata with the existing usage poll and preserve only the grant fields consumed by kandev-pacer through snapshot normalization. Never publish unrelated provider fields.

Keep the existing quota windows, stale handling and 429 retry scheduling. Add offline tests for collection, normalization and recovery so the pacer can share this one Claude poll without losing reset support.

## Implementation

Merged `30f20eb`. The existing Claude quota poll requests
`cedar_ember=1&skip_spend=1` and stores allowlisted reset-grant metadata in its
snapshot. Normalization preserves that metadata and discards unrelated provider
fields. Compact phone/watch output is unchanged. Existing stale handling and
persisted retry deadlines remain in force.

## Validation and deployment

- All **108 offline tests** passed; Ruff, ty and whitespace checks passed.
- An installed collector-to-snapshot-to-pacer check retained quota and grants
  with one mocked collector request and no supplemental request.
- Restarted the collector and configured [kandev-pacer] to share its snapshot.
  The collector retained its cooldown across restart. Its first eligible normal
  retry succeeded at **19:11:52 Helsinki time on 2026-10-26**, producing fresh
  Claude quota and grants and clearing retry/stale state. The installed pacer
  read them without another HTTP request. Both services are active.

## Evidence follow-up

Antti accepted [the retained-evidence investigation] on 2026-10-31. That work
recovered a saved success summary and reproduced the October 28 request
counts, but did not recover continuous history or establish why rate limiting
occurred. This delivery remains unaccepted; no defect or cause is established.

- **Owner:** steward.
- **Next action:** prepare a decision proposal for Antti that explains whether
  the existing evidence can satisfy the acceptance policy. If it cannot,
  specify the smallest additional evidence needed, how it could be obtained,
  and any permissions required. Do not repeat the expired-history check or
  start live requests, restarts, deployments or retention changes under this
  task's existing authorization.

No automatic experiment or service change follows acceptance of the
investigation. Antti's acceptance of this delivery remains separate.

[the retained-evidence investigation]: 32-recover-retained-runtime-evidence-for-reset-grant-snapshots.md

[kandev-pacer]: http://tinni/prg/kandev-pacer/?f
