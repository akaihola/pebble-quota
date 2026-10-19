# Make temperature units and entity age explicit

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Lower-priority temperature item from the review. collect_temperature reads
temperature as Celsius and ignores unit metadata and observation time.

## Acceptance criteria

- Define supported HA units and entity-age policy. Validate Celsius metadata or
  document a verified deployment constraint; convert Fahrenheit correctly or reject
  it explicitly. Omit unknown/stale readings rather than label them Celsius.
- Mock tests cover Celsius, Fahrenheit, missing/unknown units, stale/missing time,
  unavailable entities and HA errors. Quota delivery remains independent of HA.
- Document supported units and freshness; no live HA credentials in tests. Integrate
  temperature display freshness with proposal [9] when that proposal is promoted.
