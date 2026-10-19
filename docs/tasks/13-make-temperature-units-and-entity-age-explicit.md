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

## Implementation plan

Authorized by the explicit HAI-13 implementation request on 2026-10-19.

- Accept weather `attributes.temperature_unit` of `°C` or `°F`; convert
  Fahrenheit to Celsius before rounding to integer tenths. Reject missing or
  unknown units and nonnumeric/nonfinite values.
- Require a timezone-aware `last_updated` no more than two hours old and no
  later than the collection clock. Use this as a conservative entity-age proxy,
  not a verified meteorological observation time. No fallback to `last_changed`
  or the current collection time. Two hours allows hourly weather updates plus
  collection delay; unchanged entities can be omitted conservatively.
- Keep the existing optional temperature payload and quota error isolation.
  Mock HA, credentials and time for unit, timestamp and failure cases; verify
  quota delivery with the real temperature collector under mocked HA failures.
- Document the policy and its limits. Proposal [9] remains unpromoted; display
  expiration and original observation-time transport belong to that follow-up.
- Run the full unittest suite, Python compilation and whitespace checks, review
  the diff, merge on main and complete HAI-13 without user acceptance.
