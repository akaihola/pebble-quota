Steward issue, 2026-10-22 05:11 refill. Goal: agentic-leverage (pebble-quota is tier 1 in `<steward-vault>/Goals.md`). Estimated 45 min. From F5 and draft D1 of [the 2026-10-22 docs review](../reviews/2026-10-22-docs-review.md).

Agents' automatic edit check runs Ruff and `ty` on every edit here, and both report the same findings on unchanged `main`: seven from Ruff and four from `ty` (optional timestamp and server typing, style and file-mode findings). Every worker therefore starts from red checks and has to tell old findings from new ones. The [README](../../README.md) documents only the unittest command.

## Work

1. On `main`, run `ruff check .` and `ty check`, and record the eleven findings in this task record.
2. Fix each one without changing behaviour. Keep each provider's failure isolated from the others. For a file-mode finding, set the executable bit or drop the shebang, whichever matches how the file is run.
3. If a finding is a false positive, silence it narrowly (one rule, one file) with a comment that says why; never disable a rule for the whole repository.
4. Add both commands to the README's "Tests and status" section, beside the unittest command.

Leave out CI integration: the proposal "Gate releases on collector and phone behavior checks" ([7]) owns it.

## Acceptance

- `ruff check .` and `ty check` exit 0; `python3 -m unittest discover -s tests -v` passes all 66 tests, unchanged.
- No change to what the collector reads, writes or serves.
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

[7]: 7-gate-releases-on-collector-and-phone-behavior-checks.md
