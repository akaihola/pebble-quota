# Documentation review, 2026-10-22

Reviewed current local main at `9a572d2` (application source unchanged from the
pre-start `3ae98d2`). Scope: source and text only. No provider, production
service, device, phone, emulator or release was contacted. Text corrections are
implemented; uncertain behavior is recorded below for steward decisions.

## Coverage

The complete pre-change `git ls-files '*.md'` inventory outside the tracker,
task descriptions and earlier reviews contained five documents. All were read,
starting with the root README and agent instructions:

| Document | Result |
| --- | --- |
| [Project entry point] | Shortened; detailed collector behavior moved to a reference |
| [Agent instructions] | Tracker reference made clickable |
| [Dated architecture review] | Read in full, including its 2026-10-19 status; preserved as historical evidence |
| [Collector spike] | Marked historical and linked to production |
| [Watchface guide] | Corrected build, settings, rendering and verification claims |

Read all text files in `git ls-files collector watchface`: the [collector
source], [watch renderer], [phone transport], [build script], [build recipe],
[Nix shell], [watchface package] and watchface guide. The remaining tracked PNG
has no comments/docstrings and was not visually revalidated. Also checked the
[workflow], [release configuration], [release manifest], [prototype source],
[test suite], tracker rules and relevant task records as evidence. The new
[collector reference] was checked against the same implementation.

The architecture review's old counts and outstanding-work claims are dated
observations, not current guarantees. In particular, snapshot validation,
temperature checks, security fixes and Codex RPC handling have since landed;
this review does not rewrite that history or previous task descriptions.

## Changes and matching code

- **[Project entry point]:** replaced duplicated protocol, retry, temperature and
  release detail with links to their owning guides. Quick-start commands match
  collector `main`; offline test description matches `setUpModule` in the test
  suite. Qualified live-status claims and stated the missing CI behavior gate,
  matching the workflow's build/release jobs.
- **[Collector reference] (new):** centralized existing collector detail and
  completed the option/environment defaults (`main`, `collect_claude`,
  `collect_codex`, `collect_temperature`), startup/cadence and single-writer
  boundary (`refresh_forever`, `before_attempt`, `write_snapshot`). The full
  `v/at/q/t` and row schema, Fable code, rounding, row order and five-row limit
  match `compact_watch`, `pace_points` and sorted snapshot writes. Validation,
  fixed diagnostics, owner-only atomic writes, 401/404/503 responses and
  unauthenticated configuration match `normalize_window`, `normalize_snapshot`,
  `diagnostic`, `write_snapshot` and `make_handler`. Corrected blanket temperature
  omission to account for `refresh_snapshot` retaining old temperature when no
  usable rows remain. Distinguished that fallback from `collect_all` retaining
  Claude rows; described Codex disappearance on partial failure and omission of
  stale/error metadata from compact output. Cooldown reset wording matches the
  replacement of service state in `collect_all`. RPC deadline/cleanup wording
  matches `collect_codex`. Display freshness matches phone `sendQuota` and C
  `canvas_update` / `inbox_received`; it makes no new expiry guarantee.
- **[Watchface guide]:** replaced fixed SDK 4.17 with the build recipe's active
  SDK/`PEBBLE_CC` selection and the workflow's actual pins. Build environment
  wording matches `env -i`. Corrected the configuration URL derivation and
  removed “always reachable,” matching phone `configUrl`. Consolidated endpoint
  and token setup; documented localStorage, blank-field behavior, query-token
  prefill, cadence and lack of retry/ordering checks from `setting`,
  `webviewclosed`, `refresh` and event handlers. Rendering descriptions match
  `pace_color`, `relative_day`, `canvas_update`, `draw_combined_gauge` and
  `inbox_received`: nearest-degree rounding, conditional rows, unchecked shared
  marker assumption and in-memory state. Calendar/emulator evidence is historical,
  since no harness is tracked. Release description matches workflow job order,
  artifact naming, token fallback and the release configuration.
- **[Collector spike]:** preserved the original experiment's observations while
  removing it as a current run entry point. Its obsolete `fraction` heuristic,
  raw exception output and old adapters are visible in the prototype. Linked to
  the implemented production service rather than leaving promotion as future work.
- **[Agent instructions]:** linked the existing tracker destination; no workflow
  rule changed.
- **[Collector source]:** corrected docstrings/comments for `CodexError`
  (`diagnostic` enforces the allowlist), `epoch` (ISO subseconds truncate),
  `CLAUDE_LIMIT_WINDOWS` / `claude_windows_from_limits` (only supported windows
  and Fable scope), and `before_attempt` (persisted refresh interval, not a
  provider-wide rate-limit guarantee). Function bodies are unchanged.
- **[Watch renderer]:** corrected `s_has_temp` to describe the latest message,
  limited the `relative_day` DST claim, made unchecked reset/duration pairing
  explicit in `draw_combined_gauge`, and corrected the rounding comment in
  `canvas_update` to nearest with ties away from zero. Removed the repeated
  assertion that the weekly windows necessarily reset together.
- **[Phone transport]:** the default-endpoint comment now names saved settings,
  matching `setting` and `webviewclosed`, rather than suggesting localStorage
  overrides are only for tests.
- **[Build script]:** replaced template customization prose with a description
  of the existing SDK loader and configured platforms. Build logic is unchanged.
- **[This task's record]:** added the required plan, verification, memory and
  handoff evidence. Other task files and earlier reviews remain unchanged.

## Uncertainties and proposed answers

- **F1 — freshness policy:** whole-snapshot fallback retains temperature and
  its old collection time; retained Claude rows can instead publish with a new
  collection-pass timestamp. Neither path transports provider stale status or
  a temperature observation time. A synthetic mocked fallback confirmed old
  temperature survives. It is unclear what maximum display age is acceptable.
  Proposed answer: settle observation timestamps and expiry under the existing
  [freshness proposal]; preserve current behavior in this text-only change.
- **F2 — weekly pairing:** C pairs `C/7d` and `F/7d` by identity and draws
  Claude's marker for both. Neither provider validation nor the renderer proves
  equal resets/durations. Proposed answer: retain the proposed equality check and
  separate-row fallback in the [five-row contract proposal]; do not claim live
  resets always match.
- **F3 — settings recovery and reinstall persistence:** `configUrl` depends on
  the saved endpoint and includes the service token; localStorage alone cannot
  prove survival across phone-app reinstalls. Proposed answer: keep these as
  unresolved requirements of the [settings recovery proposal], with later
  authorized device evidence. Source existence supports a settings feature,
  not guaranteed recovery or reinstall behavior.
- **F4 — operational/release evidence:** no tracked service/proxy definitions
  establish the live host state. The package is `0.2.0`, while the release
  manifest is `0.1.0`; this difference alone does not prove a release bug.
  The calendar harness is absent, and recent Codex tests use fake servers only.
  Proposed answer: complete the existing [operations proposal] with authoritative
  host configuration, release history/retry evidence and reproducible checks;
  retain installed-CLI verification under the [Codex adapter task]. No manifest,
  deployment or historical review was changed based on inference.
- **F5 — baseline lint/type policy:** the automatic edit check runs Ruff and
  `ty`, although the repository documents only the unittest command. Both tools
  report exactly the same diagnostics on unchanged main and on these edits.
  Proposed answer: decide project checker scope and fix existing findings in a
  separate code change; do not change executable code or suppress diagnostics
  during this documentation review.

## Verification

The documented unittest command passed before and after the text changes:
**66 tests, zero failures/errors/skips**, Python 3.14.7. Test names and results
match, and the test file is byte-identical. JavaScript syntax, CLI help,
executable-content comparison, documentation links and whitespace also passed;
see [this task's record] for commands and memory measurements. Python ASTs
excluding docstrings, and C/JS content excluding comments, match main. Build
configuration and test content are unchanged; no formatting exception was needed.

Ruff exits 1 with the same seven baseline findings: `EXE001`, `UP035`, `PYI041`
and four `BLE001`. `ty` exits 1 with the same four baseline findings: one
optional-timestamp subtraction and three missing `BaseServer` attributes. These
are existing limitations, not passing checks; no diagnostic was added by this
change. The repository specifies no formatter/import-order command.

No PBW build, emulator, phone, watch, live provider, service restart or release
run was performed. This is a source/text check; it does not renew the historical
runtime evidence or establish installed CLI compatibility.

[Project entry point]: ../../README.md
[Agent instructions]: ../../AGENTS.md
[Dated architecture review]: ../2026-09-19-architecture-review-and-remediation-plan.md
[Collector spike]: ../../spikes/001-quota-collectors/README.md
[Watchface guide]: ../../watchface/README.md
[collector source]: ../../collector/pebble_quota.py
[watch renderer]: ../../watchface/src/c/watchface.c
[phone transport]: ../../watchface/src/pkjs/index.js
[build script]: ../../watchface/wscript
[build recipe]: ../../watchface/Makefile
[Nix shell]: ../../watchface/shell.nix
[watchface package]: ../../watchface/package.json
[workflow]: ../../.github/workflows/build.yml
[release configuration]: ../../release-please-config.json
[release manifest]: ../../.release-please-manifest.json
[prototype source]: ../../spikes/001-quota-collectors/probe.py
[test suite]: ../../tests/test_pebble_quota.py
[collector reference]: ../collector.md
[this task's record]: ../tasks/18-check-pebble-quota-s-documents-docstrings-and-comments-against-current.md
[freshness proposal]: ../tasks/9-carry-freshness-and-failure-status-through-to-watch-rendering.md
[five-row contract proposal]: ../tasks/11-enforce-the-five-row-collector-phone-and-watch-contract.md
[settings recovery proposal]: ../tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[operations proposal]: ../tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[Codex adapter task]: ../tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md

## Draft issues

No issues were filed. Existing proposals already own freshness, configuration,
consumer validation, phone response ordering, CI behavior gates and operational
recovery. The factual documentation portions of the operations proposal are
partly satisfied here; its deployment/recovery acceptance remains open.

- **D1 — define and reconcile Python checker policy.** Evidence: F5's unchanged
  seven Ruff and four `ty` findings. Proposed scope: choose explicit repository
  checker configuration, address the optional timestamp/server typing and
  style/file-mode findings without weakening provider failure isolation, and
  integrate the chosen checks with the existing CI behavior-gate work. Acceptance:
  documented checks pass alongside the unchanged provider-isolated tests. This
  is a steward candidate, not authorization for a code change in this task.
