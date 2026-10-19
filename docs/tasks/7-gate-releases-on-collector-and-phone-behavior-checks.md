# Gate releases on collector and phone behavior checks

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F5 / Step 3, plus remaining Step 1 regression coverage. Build workflow
has PBW metadata checks but never invokes Python or JS behavior tests.

## Acceptance criteria

- PR/main CI runs unittest with a declared compatible Python and built-in Node
  VM/assert fixtures; release creation/publishing require their success. Preserve
  PBW archive, identity, platform and version checks.
- Exercise Codex through a fake app-server, plus both Claude payload adapters:
  0, 0.5, 1, 2, 100 and missing usage. Assert fractions, compact u:1 and pace at 1%.
  Existing fixes 9fff907/5001e41 must stay intact; no live credentials in CI.
- Settings and JSON/AppMessage fixtures run without Pebble hardware; subsequent
  fixes extend these checks rather than adding a test framework.
- Demonstrate a deliberately failing assertion blocks the release dependency
  path in a disposable test context; restore it and show the suite passes.
  Record CI execution evidence separately if runner access is unavailable.
