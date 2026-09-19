---
dependencies: []
---

# Fix Codex 1% showing as 100%

## Problem

Codex returns `usedPercent: 1` for 1% usage, but `fraction()` treats values at
or below 1 as fractions, so the watchface shows 100%.

## Plan

1. Convert Codex `usedPercent` from percent to fraction unconditionally.
2. Add regression tests for 0%, 1%, and 100%.
3. Run the collector tests and verify a live snapshot matches Codex.

## Acceptance criteria

- Codex `usedPercent` values of `0`, `1`, and `100` produce `used_fraction`
  values of `0.0`, `0.01`, and `1.0`, respectively, with regression coverage.
- The collector tests pass with `python3 -m unittest discover -s tests -v`
  from the repository root.
- A live snapshot agrees with Codex usage; 1% usage displays as 1% on the
  watchface.
