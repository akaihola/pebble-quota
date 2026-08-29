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
