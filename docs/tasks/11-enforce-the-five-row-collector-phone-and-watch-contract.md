---
depends-on: [8, 9]
---

# Enforce the five-row collector phone and watch contract

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F7 / Step 7. Phone silently slices to five and ignores v; C numeric
tuples are unchecked and Claude/Fable pair solely by name.

## Acceptance criteria

- Specify deterministic priority/selection for five rows, keeping core Claude/Codex
  windows visible under extra scoped models; separate bounded wire identity from
  arbitrary display names. Reject unsupported versions explicitly.
- Validate required row fields, finite integer ranges and bounded strings in JS;
  reject malformed updates atomically. Validate C tuple type/length and coherently
  replace rows, without stale labels/partial state. Combine Claude/Fable only when
  reset and duration both match; mismatches obey the capacity policy.
- Python/Node/minimal host C fixtures cover 0/1/5/6+ rows, scoped/long names, bad
  versions, missing/wrong fields/tuples and mismatched resets. No schema generator.
- Check message keys against package.json and prove a valid five-row message fits
  2048 bytes. Inspect Emery captures for five unpaired rows and stale status; record
  any missing SDK/emulator prerequisite rather than claiming visual verification.
- Document compatible additions or a deliberate version transition and paired rollback.
