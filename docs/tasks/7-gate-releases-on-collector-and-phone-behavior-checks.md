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

## Result (2026-11-13)

**Who is affected:** Antti, when a watchface release is cut, and anyone
installing that release. **The problem:** the GitHub workflow built and released
the watch bundle without running the collector, phone-script or watch-rule
tests. A regression such as 1% usage shown as 100% could therefore ship.
**What changed:** a new `test` job runs the whole unittest suite on every pull
request and push to `main`. Release creation (`release-please`) and publishing
(`publish`) now need it as well as the bundle build. **What is different:** a
failing behaviour test now stops a release instead of being ignored.

### Changes

- [The CI workflow](../../.github/workflows/build.yml?f): new `test` job on
  Python 3.11 (the oldest the README supports) and Node 24, running
  `uv run --no-project --python 3.11 python -m unittest discover -s tests -v`.
  It sets `PEBBLE_QUOTA_REQUIRE_WATCH_TOOLS=1`, so a missing `node` or `cc`
  fails the phone and watch tests instead of skipping them. `release-please`
  needs `[test, build]`; `publish` needs `[test, build, release-please]`. The
  PBW archive, UUID, `emery` platform and version checks are unchanged.
- [The test suite](../../tests/test_pebble_quota.py?f):
  - `PERCENT_CASES` lists 0, 0.5, 1, 2 and 100 percent with the expected
    `used_fraction`, compact `u` and pace `p` half way through a 5-hour window
    (1% gives `u` 1 and `p` 49; the old 100% misreading would give -50).
  - `CodexRPCTests.test_percentages_through_the_fake_app_server` runs every
    case through the generated fake `codex app-server`; missing `usedPercent`
    yields "Codex rate limits: invalid result".
  - `ClaudeCollectTests.test_both_payload_formats_convert_percentages` runs
    every case through the `limits[]` and the legacy `five_hour` payloads; a
    missing percentage leaves no watch row. It replaces the two 0/1/100 tests.
    The fixes 9fff907 and 5001e41 are unchanged and covered by these cases.
  - `WatchTools.setUpClass` honours `PEBBLE_QUOTA_REQUIRE_WATCH_TOOLS`.
  - `SecurityTests.test_build_and_clean_scrub_environment` failed on `main`
    since issue 33 (a84b8b1): with no SDK in the test's temporary home, make
    ran the fake `pebble sdk install` and stopped. The test now creates a fake
    active SDK there, so it checks only the scrubbed environment again.
- [The README](../../README.md?f) describes the CI test job and the new setting.

The settings, JSON and AppMessage fixtures (`PhoneContractTests`,
`PhoneSettingsTests`, `WatchDecodeTests`, `WatchPipelineTests`) already ran
under Node's `vm` module and a host-compiled C driver, without Pebble hardware;
they now run in CI. Later fixes should add cases to this suite.

### Verification

- Full suite on Nix Python 3.11.17 with `PEBBLE_QUOTA_REQUIRE_WATCH_TOOLS=1`:
  118 tests, OK, none skipped (exit 0, sandbox off for `nix-shell`).
- Full suite on system Python 3.14.8 with the same setting: OK after the SDK
  test fix. Before it, that test failed on unchanged `main` too.
- The uv-managed Python 3.11.16 on this host additionally fails
  `test_codex_fake_receives_only_allowlisted_environment`, on unchanged `main`
  as well: its NixOS loader shim adds `LD_LIBRARY_PATH` to child processes. This
  is a host artefact; GitHub's Ubuntu runner has no such shim.
- `actionlint 1.7.12` on the workflow: no findings. `ruff check tests/`: no
  findings. `ruff check .` reports 6 pre-existing UP017/FURB162 findings in
  `collector/pebble_quota.py` and `spikes/`; `ty check` reports 1 pre-existing
  `invalid-mutable-override` in `collector/pebble_quota.py`. Neither file was
  changed here.

### Deliberate failure demonstration

In a disposable detached worktree of commit 8ac3eed under `$TMPDIR`, the 1% case
was changed to expect `used_fraction` 1.0 (the old bug). The CI test command then
exited 1 with three failures (`limits` and `legacy` Claude adapters, Codex fake
app-server; `AssertionError: 0.01 != 1.0`). A small evaluator read the
workflow with PyYAML and applied GitHub's rule that a job is skipped when one
of its `needs` did not succeed and its `if` uses none of `always()`,
`failure()` or `cancelled()`. With `test` failed it reported `release-please`
and `publish` as skipped; with `test` passed it reported both as running. The
worktree was then removed and the unmodified suite passed (above).

**Limit:** no GitHub Actions runner was used. The branch was not pushed, so CI
execution evidence on GitHub remains to be collected after the next push to
`main` (the first run of the `test` job).

### Guarded heavy commands

All started at once; MemAvailable stayed about 43-45 GiB, swap free 11.2 GiB of
23.6 GiB at the start with no growth observed.

| Command | Admission / final MemAvailable | Elapsed | Status |
| --- | --- | --- | --- |
| Full suite, uv Python 3.11.16 | 45.9 / 45.1 GB | 15 s | exit 1 (host artefact, see above) |
| Full suite, Python 3.14.8 | about 45 GB | 15 s | exit 1 before SDK fix |
| Full suite, Nix Python 3.11.17 | 45.1 / 45.2 GB | 22 s | exit 0 |
| Demonstration suite with injected failure | about 45 GB | 15 s | exit 1 (expected) |

No related child or forked threads were started.
