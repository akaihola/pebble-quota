# Simplification review, 2026-10-25

One modest test-harness cleanup is worth doing: share the loopback HTTP server
lifecycle and remove an unused pipeline-helper option. No production rewrite
offers a confirmed benefit large enough to recommend here. Most of the added
tests specify distinct failure, ordering and compatibility behaviour.

## Commit and scope

Reviewed local `main` at `3a963b0df7dc941ce80598082e0b6705b258718c`, against
the [architecture review]'s `61ebe07c4ba9e377f14980ceee761dcd284e68d1`.
Every source line citation below refers to the reviewed commit. The subsequent
review-plan commit changes only this issue's documentation.

Read these four feature commits first: `20644d3` (freshness), `c9de5a5`
(five-line contract), `17031b0` (zero-byte strings), and `e225b15` (response
ordering). Then reviewed the combined diff, including the completed collector
refactors, with:

```bash
git diff 61ebe07 main -- . ':!docs' ':!TASKS.md'
```

That diff contains 11 files, 1,815 additions and 358 deletions. Read the changed
production code, test cases, host drivers, message keys and guides; traced the
candidate callers and compared the open proposals in [the task tracker].
Applied Honey's preference for deletion, existing helpers and standard-library
tools. No installed `codebase-design` skill was found. Its requested vocabulary
is useful here: a **deep module** hides lifecycle details behind a small
interface; **temporal coupling** makes callers repeat an action sequence.

This report changes no implementation or tests and files no issues. No service
was restarted and no real provider was contacted. The offline test guard stays
enabled. Execution results and resource measurements belong in [the task record].

## Findings ranked by removal and risk

Estimates are net source lines after the proposed helper, not measured patches
or runtime claims. There is one finding worth a draft; minor local edits are
grouped with it rather than filed separately.

- **F1 — Own the HTTP test lifecycle in one helper.** Rank 1; approximately
  15–25 lines removed, plus one unused argument and conditional; low risk,
  confined to tests. Draft D1.

  **Evidence:** the new pipeline setup at
  [tests/test_pebble_quota.py:1566–1573][tests] repeats the loopback bind,
  snapshot/token assignment, background serving thread and ordered cleanup
  already present in the touched HTTP tests at
  [tests/test_pebble_quota.py:422–437, 447–476][tests] and the expanded damaged
  snapshot test at [tests/test_pebble_quota.py:1129–1135, 1200–1203][tests].
  These four sites contain about 36 lifecycle/scaffolding lines; a small
  context manager and four uses should retain roughly half of them. Payloads,
  URLs, tokens and assertions remain local to each test.

  **Confirmation:** read each enclosing test and its requests. All four use
  the same `QuotaServer` and `Handler`, bind `127.0.0.1` with an ephemeral port,
  and require `shutdown`, `server_close`, then `join(timeout=2)`. The pipeline's
  three `addCleanup` calls execute in that same reverse-registration order.
  Its temporary snapshot and provider mocks outlive the server cleanup.
  This is duplicated resource ownership, not duplicated contract validation.
  A standard-library `contextlib.contextmanager` can own that temporal coupling;
  `TestCase.enterContext` is already used throughout the new harness.

  **Related small deletion:** `WatchPipelineTests.view` at
  [tests/test_pebble_quota.py:1616–1620][tests] accepts `watch_now`, but every
  repository call is `self.view()` with no argument. The reset, offline-age,
  skew and marker tests instead call `self.watch(message, now)` directly at
  [tests/test_pebble_quota.py:1727–1790][tests]. Keep that lower-level clock
  seam; remove the unused override and conditional from `view`.

  **Risk:** broadening the shared fixture into provider setup or changing its
  lifetime could weaken isolation. Limit it to the existing running HTTP
  server lifecycle. The busy-port test at
  [tests/test_pebble_quota.py:885–892][tests] only reserves a socket and must
  retain its separate setup.

  **Recommendation:** use one local context manager with explicit snapshot
  and token inputs, yielding the server. Keep assertions and fixtures in
  their existing test classes; no new framework, configuration flags or file.

## Candidates deliberately not drafted

- **Collector pace and watch pace:** the collector still emits `p` at
  [collector/pebble_quota.py:565–571][collector], while the watch derives colour
  from its current marker at [watchface/src/c/gauges.c:91–100, 154–162][gauges].
  This is intentional compatibility, confirmed by the [wire contract] and
  `WatchPipelineTests.test_reset_crossing_hides_old_usage_even_when_recent`
  at [tests/test_pebble_quota.py:1727–1739][tests]. Deleting `p` would change
  old-bundle behaviour; using its cached value would break colour ageing.
- **Repeated wire identity lookup:** `normalize_window` validates labels at
  [collector/pebble_quota.py:123–132][collector]; `compact_watch` obtains their
  wire identity again at [collector/pebble_quota.py:558–564][collector]. The
  decision already has one implementation. Carrying its result through
  normalization would add internal metadata or another return shape to avoid
  a small lookup. `CompactSelectionTests.test_scope_display_names_never_reach_the_wire`
  at [tests/test_pebble_quota.py:1870–1887][tests] confirms why snapshot labels
  and wire identities remain different. No smaller confirmed design emerged.
- **Phone ordering state:** [watchface/src/pkjs/index.js:65–118][phone] uses
  request sequence for supersession, endpoint/token for history reset, and
  collector/phone timestamps for bounded regression rejection. The six
  ordering/failure tests at [tests/test_pebble_quota.py:1947–2020][tests]
  exercise these independently. Removing one state dimension would change
  behaviour; a request queue or generic state machine would add machinery.
- **Watch boundary and host tools:** `decode_message` owns tuple validation
  and fills scratch space; [watchface/src/c/watchface.c:268–285][watch] commits
  it only on success. The host driver follows the same rule at
  [tests/watch/gauges_main.c:64–88][driver]. `WatchTools` already shares phone
  execution and C decoding at [tests/test_pebble_quota.py:1478–1532][tests].
  Removing these seams, width/string cases or validation in another layer
  would lose useful independent checks.
- **Tiny production edits:** making the two internal gauge helpers private
  would remove two declarations at [watchface/src/c/gauges.h:77–78][gauge-api];
  the caller search finds only uses inside [watchface/src/c/gauges.c:154–162][gauges].
  Changing the opposing `windows` checks to `if/else` at
  [collector/pebble_quota.py:508–511][collector] would shorten one expression.
  Neither justifies a separate issue. Keep the decoder and rendering guards.

## Existing issue coverage

[Settings recovery] already owns settings transport and recovery changes;
[the release behaviour gate] owns CI execution and its release dependency;
[operational documentation] owns deployment/build/recovery reconciliation.
Those are not new drafts here. The earlier architecture drafts were completed
as the [HTTP publication simplification], [Codex decoder extraction],
[fallback merge extraction] and [collector helper cleanup]; this review does
not reopen them. Security questions remain with [the security fixes].

D1 has no open-issue duplicate: sharing an existing test resource fixture does
not add the release gate or change its required behaviour coverage.

## Do these first

- **D1:** consolidate the four HTTP-server lifecycles and remove the unused
  `view` override in the same test-only change.

**Recommendation:** do D1 when next maintaining these tests. Keep production
behaviour and the existing contract tests intact; there is no urgent rewrite.

## Draft issues

These are unfiled proposals for the steward.

- **D1 — Share the loopback HTTP fixture in quota tests.** Covers F1.

  **Why:** four tests repeat resource ownership and teardown order; the new
  pipeline helper also exposes a clock option that no caller uses.

  **What to change:** add one local `contextlib.contextmanager` in
  [tests/test_pebble_quota.py][tests] accepting the snapshot path and token,
  binding the existing server to loopback on port zero, yielding that server,
  and closing/joining it in `finally`. Use it in the two `HttpTests` methods,
  `ValidationTests.test_http_damaged_state_and_diagnostics_are_sanitized`, and
  `WatchPipelineTests.setUp`. Preserve cleanup before temporary files and mocks
  disappear. Remove `view(watch_now=...)` and always use `self.now` there.
  Leave the socket-only busy-port test, provider fixtures and `WatchTools`
  unchanged. Do not widen subprocess or network permissions.

  **Preservation checks:** run
  `HttpTests.test_config_page_served_without_auth`,
  `HttpTests.test_watch_endpoint_requires_bearer_token`,
  `ValidationTests.test_http_damaged_state_and_diagnostics_are_sanitized`,
  `StartupTests.test_busy_port_does_not_collect`, and all `WatchPipelineTests`.
  In particular, retain `test_healthy_claude_429_cooldown_and_recovery`,
  `test_offline_phone_ages_rows_and_temperature`,
  `test_reset_crossing_hides_old_usage_even_when_recent`,
  `test_future_timestamps_beyond_the_skew_are_not_fresh` and
  `test_missing_temperature_and_colour_follows_the_marker`. Run the full
  offline suite, `ruff check .` and `ty check`; require Node and the host C
  compiler so the pipeline tests actually execute. Inspect the helper's
  `finally` and context lifetimes to preserve cleanup on assertion failure.

  **Acceptance:** all named tests retain their assertions and pass without
  skips; four lifecycle copies become one, every `view` caller remains valid,
  and the server still shuts down, closes and joins within its existing
  teardown policy. No production file, protocol, publication policy or
  provider-access guard changes. Net test source is smaller. No deployment,
  device check or real provider request is needed for this refactor.

[architecture review]: 2026-10-22-architecture-review.md
[the task tracker]: ../../TASKS.md
[the task record]: ../tasks/27-review-pebble-quota-s-changes-since-the-10-22-architecture-review-for-.md
[tests]: ../../tests/test_pebble_quota.py
[collector]: ../../collector/pebble_quota.py
[gauges]: ../../watchface/src/c/gauges.c
[gauge-api]: ../../watchface/src/c/gauges.h
[phone]: ../../watchface/src/pkjs/index.js
[watch]: ../../watchface/src/c/watchface.c
[driver]: ../../tests/watch/gauges_main.c
[wire contract]: ../collector.md#http-and-compact-payload
[Settings recovery]: ../tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[the release behaviour gate]: ../tasks/7-gate-releases-on-collector-and-phone-behavior-checks.md
[operational documentation]: ../tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[HTTP publication simplification]: ../tasks/21-use-one-compact-payload-decision-for-http.md
[Codex decoder extraction]: ../tasks/22-separate-codex-result-decoding-from-rpc.md
[fallback merge extraction]: ../tasks/23-isolate-the-unavailable-snapshot-merge.md
[collector helper cleanup]: ../tasks/24-remove-unused-collector-helper-generality.md
[the security fixes]: ../tasks/16-fix-the-collector-and-build-findings-of-the-2026-10-21-security-review.md
