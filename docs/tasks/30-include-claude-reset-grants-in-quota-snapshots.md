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

Completion awaits user acceptance.

[kandev-pacer]: http://hopeli/prg/kandev-pacer/?f
