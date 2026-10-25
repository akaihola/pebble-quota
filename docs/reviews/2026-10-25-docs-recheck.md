# Documentation recheck, 2026-10-25

Reviewed local `main` at `8186753`, whose latest source change is `b9e6118`.
All three requested documents were read in full: the [project entry point],
[agent instructions] and [collector reference]. The [watchface guide] was also
read to consolidate repeated policy descriptions. The [dated architecture
review], earlier reviews and other task records remain unchanged.

This is a source review. No collector restart, live configuration or credential
access, provider request, installed CLI probe, watch build or installation was
performed. The [previous documentation review] remains historical evidence.

## Ten source changes

The requested inventory returned exactly these ten commits, oldest first:

```bash
git log --no-merges --reverse 418b500..main -- . ':!docs' ':!*.md'
```

Unless noted below, the commits leave payload fields, settings, persistent
files and user-visible messages unchanged. Source evidence is in the
[collector], [phone script], [gauge module], [watch renderer], [message manifest]
and [offline tests].

- **`505c04b` — clear Ruff and ty findings:** removes nonexecutable Python
  shebangs, corrects annotations/imports, narrows the optional timestamp and
  types the HTTP server. Broad exception boundaries remain, with reasons.
  Test fixtures use typed headers and `Self`; tests need Python 3.11 or newer.
  The entry point documents unittest, Ruff and ty. No runtime contract change.
- **`96e0f85` — one HTTP payload decision:** `Handler.do_GET` uses the result
  of `compact_watch` for both availability and the response body. Empty rows
  or a missing valid timestamp still return 503 `Snapshot unavailable`;
  validated sibling rows still survive damaged snapshots.
- **`96dba4d` — separate Codex result decoding:**
  `codex_service_from_result` handles wrapped and direct rate-limit results,
  malformed siblings and empty windows. RPC transport, deadlines, diagnostics
  and process cleanup remain in `collect_codex`; no wire or snapshot change.
- **`7a1c3a9` — isolate unavailable-snapshot merging:** the pure
  `merge_unavailable_snapshot` deep-copies prior quota, collection time and
  temperature, then merges attempted service metadata and stale ages.
  `refresh_snapshot` still writes the result and raises on a rowless attempt.
  No new output file or fallback policy.
- **`6679365` — remove unused helper generality:** a module-level `Handler`
  replaces the factory, and `iso_from_epoch` takes numeric seconds only.
  HTTP routes, authorization, caching and diagnostics are unchanged; the
  collector reference contains no remaining factory claim.
- **`20644d3` — carry freshness and failures:** records Codex `last_success_at`
  in the existing snapshot. Version 1 HTTP adds top-level `n` and row `o`/`e`;
  `p` remains for old clients. The bundled AppMessage keys add `UNAVAILABLE`
  and replace per-row `P` with `O`/`E`. The new gauge module ages readings
  against the watch clock, shows `stale`, `clock skew`, `reset ?` or
  `unavailable`, hides old temperature and computes color from the current
  marker. Claude retention and Codex disappearance on partial failure remain.
- **`c9de5a5` — enforce five lines:** `compact_watch` reserves unavailable
  lines, prioritizes core windows and selects/orders scoped extras
  deterministically. Scope names map to wire letters. The phone validates a
  whole payload; the watch validates into scratch space before replacement.
  Claude/Fable weekly rows pair only when reset and duration agree. No new
  wire field or setting; malformed data logs `Rejected quota data:` on the
  phone or `Rejected malformed quota message` on the watch.
- **`17031b0` — reject zero-byte strings:** `field_string` requires a NUL byte
  within the declared tuple length, including for empty `UNAVAILABLE`.
  Rejection keeps all previously displayed rows. Field names and limits stay
  unchanged.
- **`e225b15` — discard superseded phone responses:** only the latest started
  refresh can forward a response, even if that refresh fails. Endpoint/token
  changes reset timestamp history; decreasing collection timestamps are
  rejected for less than 15 minutes after the last forwarded response.
  Rejection does not extend the guard, equal timestamps are allowed, and
  expiry or an invalid/backward phone clock permits recovery. Logs add
  `Rejected older quota data` and explain deferred AppMessage delivery.
  No immediate retry queue, new saved setting or persistent history.
- **`b9e6118` — share the loopback test server:** `loopback_server` owns bind,
  startup, shutdown, close and join for four test lifetimes. The unused
  `view(watch_now=...)` argument is removed. Production behavior, test
  assertions and provider/credential guards stay unchanged; temporary test
  artifacts remain temporary.

## Document changes and matching evidence

- **Project entry point:** links to the collector reference instead of
  repeating five-line selection (`c9de5a5`, `compact_watch`). States the test
  suite's Python 3.11 minimum (`505c04b`, `typing.Self`, and the tests'
  `enterContext` calls). Removes the unsupported assertion that unconfigured
  tools necessarily use default rules: the local Ruff settings enable
  `BLE001`, `EXE001` and `UP035`. Points to this recheck instead of presenting
  the 10-22 review as current. The three check commands remain unchanged.
- **Agent instructions:** read and retained unchanged. They point to the
  [task tracker] and prescribe no additional validation commands. The tracker
  supplies the start, plan, worktree, merge and completion workflow.
- **Collector reference:** makes `o` explicitly a collection-pass timestamp
  (`20644d3`, `collect_all`); adds missing `n: "X"` to the Claude-only example
  (`compact_watch`). States the actual temperature bounds in `quotaMessage`
  and `decode_message` (`c9de5a5`; discrepancy F1 below). Makes zero-byte/NUL
  validation explicit (`17031b0`, `field_string`) while retaining the phone's
  string bounds. Links to the existing phone-ordering explanation
  (`e225b15`, `refresh`, `sendQuota`). Removes the claim that only a newer
  reading clears stale status: `row_state` recomputes status from the clock
  and current fields, and `refresh` accepts equal timestamps and bounded
  regressions. Links the verification environment here and keeps installed
  Codex compatibility explicitly unverified by this review.
- **Watchface guide:** replaces repeated freshness thresholds, colors, labels
  and temperature expiry with a link to the collector's owning explanation
  (`20644d3`, `row_state`, `row_status`, `show_temperature`, `plan_gauges`;
  watch `tick_handler`). Removes the same unsupported newer-only claim.
  Keeps the rendering/pairing description and the already-correct phone
  settings and response-ordering policy (`c9de5a5`, `e225b15`).
- **This task's record:** adds the implementation plan, outcome, checks and
  memory reports. The completion receipt records checks at the merged commit;
  it is the requested exception to the Markdown-only delivery.

The readable guides are shorter overall. No code, tests, formatting exception,
old review or unrelated task description was changed.

## Uncertainties and proposed answers

- **F1 — temperature lower-bound mismatch:** collector `normalize_snapshot`
  and phone `quotaMessage` accept -2147483647 through 2147483647; watch
  `decode_message` also accepts -2147483648. The normal phone path cannot
  forward that extra value. The former statement that all ranges matched was
  false; the reference now states both actual ranges. Source does not establish
  whether the wider watch range was deliberate, and the contract tests do not
  settle that boundary.

  **Recommendation:** align the watch with the collector/phone range and add
  explicit boundary cases in a separate code task; review rendering arithmetic
  at both extremes before choosing the supported range.

- **F2 — Codex child shell portability:** `collect_codex` still assigns a
  hard-coded conventional Bash path in its child environment. This predates
  the ten commits, and the reference accurately describes it. The launch
  instructions require resolving Bash on NixOS, but fake subprocess tests
  cannot establish whether an installed CLI depends on that environment value.

  **Recommendation:** resolve Bash from `PATH`, keep the environment allowlist,
  and test it without real credentials. Leave installed-CLI evidence with the
  existing [Codex adapter task] and [operations proposal]. This documentation
  change does not alter the environment or claim a live failure.

Existing settings recovery, CI behavior gates and operational/release evidence
remain with their [settings proposal], [CI proposal] and operations proposal.
No source change here establishes deployment or reinstall persistence.

## Verification

The [project entry point] supplies the validation commands. Before merging,
all 106 offline tests passed without skips, and Ruff, ty and the documentation
check passed. Checks recorded at the merged commit are detailed in
[this task's record].
The environment is Python 3.14.7, Ruff 0.16.8 and ty 0.0.84, with Node and the
host C compiler available; no minimum-Python compatibility matrix was run.
The provider-isolated suite exercises HTTP, Codex decoding, fallback merging,
freshness, row selection, message rejection and response ordering. Its host
C harness does not build or install the Pebble app.

The documentation check covers relative links/anchors, the synthetic payload,
the ten-commit inventory, preserved historical documents, permitted file scope
and whitespace. The watchface guide's existing link to a generated bundle is
an expected build artifact, not an assertion that a build was run.

## Draft issues

No issues were filed; these are steward candidates.

- **D1 — reconcile temperature bounds across consumers:** F1. Choose one
  supported range after reviewing rendering arithmetic, document it once and
  cover lower/upper limits plus adjacent rejected values in collector, phone
  and host-watch tests. Keep malformed-message replacement atomic.
- **D2 — resolve the Codex child's Bash executable:** F2. Replace the fixed
  path with executable discovery and define missing-Bash behavior. Add a
  fake-process test for the chosen environment while preserving token
  exclusion, RPC diagnostics and cleanup. Coordinate installed-CLI validation
  with the existing adapter/operations work.

[project entry point]: ../../README.md
[agent instructions]: ../../AGENTS.md
[collector reference]: ../collector.md
[watchface guide]: ../../watchface/README.md
[dated architecture review]: ../2026-09-19-architecture-review-and-remediation-plan.md
[previous documentation review]: 2026-10-22-docs-review.md
[collector]: ../../collector/pebble_quota.py
[phone script]: ../../watchface/src/pkjs/index.js
[gauge module]: ../../watchface/src/c/gauges.c
[watch renderer]: ../../watchface/src/c/watchface.c
[message manifest]: ../../watchface/package.json
[offline tests]: ../../tests/test_pebble_quota.py
[task tracker]: ../../TASKS.md
[this task's record]: ../tasks/29-check-pebble-quota-s-documents-against-the-ten-source-changes-since-th.md
[Codex adapter task]: ../tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md
[operations proposal]: ../tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[settings proposal]: ../tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[CI proposal]: ../tasks/7-gate-releases-on-collector-and-phone-behavior-checks.md
