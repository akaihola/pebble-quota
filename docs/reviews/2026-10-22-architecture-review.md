# Architecture review, 2026-10-22

Keep the current deployment and protocol. The useful simplifications are a
single HTTP publication decision, a pure Codex result decoder, and a pure
snapshot fallback merge. These reduce the context needed to change and test
the collector without introducing a framework or changing quota behavior.

## Scope and baseline

Reviewed local `main` at `61ebe07c4ba9e377f14980ceee761dcd284e68d1`.
All code line references below refer to that commit; the worktree was rebased
onto it before review. Application code includes the completed [checker fixes].
The [September architecture review] and its October status already exist,
despite this task's premise that there has been no repository review. This
report reassesses the current implementation, including the subsequent
validation and RPC fixes, rather than carrying forward their old verdicts.

Read the [project guide], [agent instructions], [collector guide], [watchface
guide], prior architecture/documentation/security reports and task criteria.
Traced all production Python, phone JavaScript, watch C, tests and build/release
configuration. The production source is 747 Python lines, 88 phone JavaScript
lines and 392 watch C lines; the Python test file is 1,231 lines. Size alone is
not a finding. The tracked inventory has no runtime/build/test dependency on
the [historical spike]; its README was checked, its collector was not executed
or proposed for maintenance. The existing screenshot was not revalidated.

Applied Honey's deletion, native-library and minimum-abstraction principles.
No `codebase-design` skill was available in this session; the review uses its
requested vocabulary directly: a **deep module** hides substantial policy
behind a small interface; **information leakage** makes callers know those
details; **temporal coupling** makes correctness depend on action order.
An extracted function earns its place through an independent policy or test
boundary, not merely by shortening its caller.

This is an architecture review, with no vulnerability probes, credential
inspection, live quota calls, service changes or draft filing. The earlier
[security review] is context, not a new security assessment.

## Boundaries worth preserving

- **Fetch:** Claude HTTP, Codex stdio RPC and optional Home Assistant reads
  have different protocols and failure rules. Their concrete functions and the
  two-entry collector tuple are enough; a provider interface/registry would
  add concepts without another actual requirement. See
  [collector/pebble_quota.py:246–446][collector] and
  [collector/pebble_quota.py:466–523][collector].
- **Cache:** the snapshot stores both display data and durable attempt/cooldown
  metadata. It is more than a disposable performance cache. The callback
  checkpoints attempts before provider calls, memory is updated before the
  final write, and atomic replacement protects disk readers. These ordering
  guarantees must survive refactoring. See
  [collector/pebble_quota.py:557–626][collector] and
  [tests/test_pebble_quota.py:833–873, 1007–1037][tests].
- **Serve:** HTTP reads only the saved snapshot and computes compact pace at
  read time. Keep that decoupling: phone refreshes must never trigger quota
  calls. The small standard-library server, two routes and typed server
  attributes fit this deployment. See
  [collector/pebble_quota.py:526–554, 629–743][collector].
- **Phone/watch:** the phone transports data and settings; the watch owns its
  in-memory rows and rendering. The drawing helpers hide real layout decisions,
  even where they have one caller. Five-row linear searches are appropriate.
  See [watchface/src/pkjs/index.js:7–88][phone] and
  [watchface/src/c/watchface.c:138–224, 322–379][watch].
- **Infrastructure:** JSON, atomic replacement, datetime parsing, HTTP serving,
  queues and process management already use the standard library. Keep
  `write_snapshot`, window validation, diagnostic filtering, the RPC deadline
  and cleanup, and the offline test guard. None is replaceable with an unsafe
  one-liner. See [collector/pebble_quota.py:71–174, 279–401, 557–567][collector]
  and [tests/test_pebble_quota.py:30–90][tests].

## Findings ranked by benefit per hour

Ranks concern maintenance benefit for a bounded change, not incident severity.
Effort includes focused tests and the existing offline checks. Draft identifiers
are local to this report; they are not tracker issue numbers.

- **F1 — HTTP repeats the snapshot publication decision.** Rank 1; high benefit
  for about 0.75–1 agent hour; low change risk. Draft D1.

  **Evidence:** [collector/pebble_quota.py:689–693][collector] first calls
  `has_quota_data`, which normalizes the entire snapshot at lines 570–572,
  then separately validates the top-level timestamp and calls `compact_watch`,
  which normalizes again at line 527. Inside that compactor, lines 534–538
  reparse/check values already guaranteed by `normalize_window` at lines
  104–117. Thus the handler and serializer both know what makes a publishable
  snapshot. Damaged-state behavior is exercised at
  [tests/test_pebble_quota.py:883–919, 1039–1066][tests].

  **What changes:** build the compact payload once, require nonempty `q` and
  non-`None` `at`, and serialize that same object. Inside `compact_watch`, use
  the validated row fields directly. This removes a whole normalization pass
  from an HTTP read and redundant row checks; the benefit is one policy owner,
  not a claimed speed improvement. Keep normalization on raw input to public
  entry points, including disk reads; do not create a `trusted=True` bypass.
  Keep the handler's existing JSON read/error handling: the forgiving
  `load_snapshot` has different diagnostic behavior.

  **Overlap:** builds on completed [snapshot validation]. It does not repeat
  that fix or change the [five-row contract proposal]'s selection/version
  policy. Missing/corrupt/rowless state must still return the existing 503.

  **Recommendation:** simplify these existing functions in place. A repository,
  service layer, schema library or new source file would enlarge this seam.

- **F2 — Codex payload rules are inside the process lifecycle.** Rank 2; high
  benefit for about 1 agent hour; low-to-medium change risk. Draft D2.

  **Evidence:** [collector/pebble_quota.py:279–401][collector] combines process
  creation, reader thread, protocol sequencing, result decoding and cleanup.
  Lines 357–382 alone decide wrapped versus legacy result shape, durations,
  percentage conversion, invalid siblings and empty-window diagnostics.
  [tests/test_pebble_quota.py:936–947][tests] builds a fake process and handshake
  to test a malformed window; lines 1169–1197 send value-shape cases through
  generated app-servers. Claude already has a pure limits decoder at
  [collector/pebble_quota.py:193–233][collector].

  **What changes:** one provider-specific pure function accepts the Codex
  rate-limit result and returns the existing service dictionary or raises the
  existing fixed diagnostic. Value-shape tests need only dictionaries; transport
  tests retain the real fake-child lifecycle. A payload adjustment no longer
  requires reasoning about pipes, thread scheduling and process teardown.

  **Overlap:** completed [Codex RPC handling] owns the implemented errors and
  cleanup; D2 preserves them. Additional adapter boundary cases from the
  [behavior-gate proposal] can reuse this seam, without filing them twice.
  Installed CLI compatibility remains unverified and outside this refactor.

  **Recommendation:** extract only the result decoder in the existing module.
  Keep the two-stage handshake and one overall deadline together. Do not build
  a reusable JSON-RPC client, abstract transport, plugin system or async rewrite.

- **F3 — fallback policy is coupled to disk effects.** Rank 3; high policy
  clarity for about 1 agent hour; medium change risk. Draft D3.

  **Evidence:** [collector/pebble_quota.py:575–615][collector] loads state,
  checkpoints attempts, collects, chooses retained quota, mutates the caller's
  memory, writes and sometimes raises after that write. The fallback at lines
  591–607 merges new scheduling/errors into old rows while preserving the old
  collection timestamp and temperature. Its tests require temporary files and
  mocked collection: [tests/test_pebble_quota.py:966–1037][tests]. Separate
  Claude retention at [collector/pebble_quota.py:507–513][collector] means both
  providers failing can still yield usable retained Claude rows and bypass the
  whole-snapshot fallback; lines 285–293 of the tests cover that distinction.

  **What changes:** isolate the whole-snapshot fallback merge as a pure
  operation on previous and attempted snapshots. It hides the old timestamp,
  temperature, stale age and new scheduling merge rules behind one small
  interface. `refresh_snapshot` keeps the effect ordering visible. Tests of
  the merge become ordinary data cases, while integration tests still verify
  restart and write-failure behavior. Preserve the current mutation of supplied
  `previous` before a possibly failing disk write: simply assigning a returned
  snapshot in `refresh_forever` would lose new cooldown state on an exception.

  **Overlap:** adjacent to the [freshness proposal], which owns any change to
  Claude/Codex retention or observation-time semantics. D3 is a characterization
  and extraction of current fallback policy only. Do not consolidate the two
  retention paths by silently making their different behavior identical.

  **Recommendation:** make this narrow extraction before changing freshness.
  Keep the attempt callback: it serves a real persistence boundary despite
  having one production caller. A generic cache/store class would obscure the
  ordering that currently protects provider polling.

- **F4 — tests stop at the Python side of the wire.** Rank 4; medium-to-high
  benefit for a 1-hour first slice of existing work; low runtime risk. Draft D4
  is an overlap refinement, not a new issue.

  **Evidence:** Python compaction, JavaScript key construction and C reception
  each describe the contract at [collector/pebble_quota.py:526–554][collector],
  [watchface/src/pkjs/index.js:11–30][phone],
  [watchface/package.json:24–63][package] and
  [watchface/src/c/watchface.c:312–345][watch]. The tracked tests contain only
  the [Python suite]; [the build workflow:12–95][workflow] runs no behavior
  tests and makes releases depend on the PBW build. A successful Python check
  cannot detect a misspelled phone message key or a dropped optional field.

  **What changes:** a tiny Node VM/assert harness captures messages from the
  actual phone script using synthetic compact payloads and compares keys with
  the manifest. Run it and Python tests as release prerequisites. This gives
  the protocol a test boundary without adding a runtime abstraction or schema
  generator. Consumer validation and rendering policy remain separate work.

  **Overlap:** directly owned by the [behavior-gate proposal], with the broader
  C/overflow/version assertions owned by the [five-row contract proposal].
  The [request-ordering proposal] can later extend the same mocked XHR harness.

  **Recommendation:** steward should refine/promote the existing gate proposal,
  not create a duplicate test-infrastructure task or split the 88-line phone
  script into modules solely for testing.

- **F5 — two collector helpers expose unused flexibility.** Rank 5; small
  benefit for about 0.5–1 agent hour; low behavior risk but indentation churn.
  Draft D5 is optional cleanup.

  **Evidence:** `make_handler` takes no arguments and captures no configuration;
  it only creates and returns a class, whose configuration comes from
  `self.server` ([collector/pebble_quota.py:667–709, 730–731][collector]).
  `iso_from_epoch` accepts `None`, numeric strings and arbitrary nonnumeric
  strings ([collector/pebble_quota.py:56–61][collector]), but both production
  calls supply arithmetic epoch values (lines 458, 502–503); repository test
  calls also supply numbers, including fractional seconds at
  [tests/test_pebble_quota.py:487–493][tests].

  **What changes:** a directly named handler class removes a factory layer;
  numeric-only timestamp formatting removes four unused branch lines and the
  optional/string return contract. Keep the datetime conversion's range errors
  because `claude_retry_delay` uses them to reject unrepresentable retry dates.
  This is deletion of shallow indirection and unused accepted inputs, not a
  newly discovered runtime defect. No entire runtime subsystem proved dead.

  **Overlap:** no open proposal requests these internal cleanups. D1 touches
  the same handler; do D5 after it, or fold the factory deletion into that change.
  Preserve the typed `QuotaServer` introduced by [checker fixes].

  **Recommendation:** defer behind D1–D4; omit the factory change if its broad
  unindent diff would conflict with active handler work. Do not preserve unused
  generality by adding another compatibility wrapper.

## Existing work and changes not justified

- **Settings and response ordering:** [settings recovery] owns the coupled
  saved endpoint/configuration route at [watchface/src/pkjs/index.js:58–79][phone]
  and [collector/pebble_quota.py:634–664][collector]. [Request ordering] owns the
  overlapping refresh callbacks at [watchface/src/pkjs/index.js:33–55, 81–88][phone].
  No separate settings service, queue framework or configuration rewrite is
  justified by this review. Phone save/reopen/reinstall evidence is still a
  device requirement of the existing settings proposal.
- **Freshness and bounded rows:** [freshness] owns observation age, expiry and
  marker/color consistency; [five-row contract] owns row selection, version
  checks, atomic C replacement and Claude/Fable pairing. Evidence remains
  [collector/pebble_quota.py:507–513, 550][collector] and
  [watchface/src/c/watchface.c:195–223, 263–295, 322–345][watch]. They change
  product behavior and must not be smuggled into D1–D3. Their existing
  dependencies remain unchanged. Emery rendering needs emulator/watch evidence;
  a physical phone is needed for the settings persistence claims.
- **Operations and build:** the [operations proposal] already covers SDK/release
  reconciliation, deployment recovery and historical calendar evidence. The
  [documentation review] completed much of its factual text, and the spike is
  already marked historical. [watchface/wscript:20–37][wscript] contains an
  unused optional worker branch: no worker source is tracked. Removing those
  template lines is possible, but an SDK build would cost more verification
  than the reading-time saving warrants. Keep the SDK platform loop and existing
  build glue; no new build-system cleanup issue is recommended.
- **Already implemented protections:** completed [snapshot validation],
  [Codex RPC handling], [temperature validation], [collector/build fixes] and
  [checker fixes] supersede the older reviews' unfixed-code claims. Backoff
  remains in [the existing backoff task]; its research limitations do not
  justify quota probes or a new polling layer. This review changes no acceptance
  state for those tasks.
- **Unnecessary redesigns:** no measured need for a database, shared in-memory
  HTTP cache, provider parallelism, persistent Codex process, third-party web
  framework, wire-code generator or general-purpose rendering layer. Do not
  remove the failure-isolation `except` blocks or tests' live-access guard.
  Comments about retry timing, watch integer bounds and rendering choices
  explain constraints; a narration-only cleanup after the recent docs review
  offers less benefit than the ranked changes.

## Verification and limits

The source review and tracked inventory establish the cited dependencies and
duplication. The unchanged offline suite passed all 66 tests with no skips;
Ruff, ty and JavaScript syntax checks passed. Report citation/link checks and
commands/resource measurements are recorded in [this task's record]. These
checks validate the reviewed baseline and report, not implementations of the
drafts.

No PBW build, emulator, phone, physical watch, live quota compatibility, deployed
service or GitHub Actions execution was verified. None is needed to complete
this report. D1–D3 and D5 can be verified entirely offline; D4's CI wiring needs
an Actions run to establish the hosted release gate. Existing device-dependent
proposals keep their verification requirements. No draft requires a live quota
request; the existing Codex compatibility follow-up must obtain separate
authorization if it needs one.

## Draft issues

These are steward drafts only. D4 belongs within an existing Unverified proposal;
D3 overlaps its neighboring freshness work in location but deliberately keeps
the current behavior. Estimated effort is per draft, including checks, not a
promise to finish the larger existing proposals in one hour.

**Recommendation:** do **D1 — Use one compact payload decision for HTTP**,
**D2 — Separate Codex result decoding from RPC**, then **D3 — Isolate the
unavailable-snapshot merge**. D1 removes duplicated publication policy with
the smallest risk; D2 makes provider-shape changes cheap to test; D3 makes the
more delicate retention policy explicit before freshness work. D4 is valuable
existing work for the steward to promote, and D5 can wait.

- **D1 — Use one compact payload decision for HTTP.** New candidate; F1;
  approximately 1 agent hour.

  **Work:** compute `compact_watch` once in the watch route, validate its `q`
  and `at`, then serialize that object. Remove checks inside the compactor
  already guaranteed by its own normalization. Keep the raw-input boundary,
  current row order/truncation, timestamp/rounding rules, diagnostic categories,
  auth handling and public helper behavior.

  **Acceptance:** authenticated loopback fixtures preserve valid and mixed-valid
  payloads, accept timestamp zero, and return fixed 503 for missing/corrupt/
  wrong-root/rowless/invalid-timestamp snapshots. Assert every serialized row is
  valid and valid siblings survive. Existing 401/404/config tests and all offline
  checks pass. A code review confirms the route no longer runs two independent
  snapshot-normalization/publication paths.

  **Overlap/verification:** follow-up to completed snapshot validation; no
  five-row policy change. Phone: no. Watch: no. Live quota: no.

- **D2 — Separate Codex result decoding from RPC.** New candidate; F2;
  approximately 1 agent hour.

  **Work:** extract the rate-limit result parsing into one pure provider-specific
  function in the existing collector file. Move value-only cases to direct
  calls; keep integration coverage of the actual handshake, notifications,
  deadline, environment and teardown. Preserve wrapped/direct formats,
  duration-based labels, sibling salvage and all diagnostic text.

  **Acceptance:** direct dictionary cases cover 0, 0.5, 1, 2, 100 and missing
  usage, bounded durations, malformed primary with valid secondary, invalid
  result and legitimate no-window results. Preserve duplicate-duration behavior
  and window order. Fake-child tests still prove EOF/timeout/RPC errors, forced
  kill, reaping and closed pipes; a 1% adapter result still compacts to `u: 1`.
  Full offline checks pass without invoking the installed Codex CLI.

  **Overlap/verification:** do not reopen completed RPC handling; coordinate
  percentage boundary coverage with the behavior-gate proposal. Phone: no.
  Watch: no. Live quota: no; installed-CLI compatibility remains separate.

- **D3 — Isolate the unavailable-snapshot merge.** New bounded refactor; F3;
  approximately 1 agent hour, before any freshness semantics change.

  **Work:** extract only the whole-snapshot fallback merge into a pure function
  with no disk, provider or clock access and no mutation of its inputs. Keep
  `refresh_snapshot` responsible for checkpoints, publication, the in-memory
  update before writes, and the existing unavailable exception. Keep Claude's
  per-provider retention and its timestamp behavior unchanged.

  **Acceptance:** pure cases preserve old quota/collection time/temperature,
  merge new attempts/cooldown/errors and compute the same stale ages; empty
  prior state stays unavailable. Input dictionaries remain unchanged. Existing
  integration tests plus a retained-temperature case distinguish both-failed
  with prior Claude from both-failed with only prior Codex, first 429 without
  rows, restart interval suppression and write failure with new in-memory
  cooldown. Full offline checks pass; persisted schema and compact payloads
  are unchanged for those sequences.

  **Overlap/verification:** related to the existing freshness proposal; merge
  or drop this extraction if that work already supplies the same seam. It does
  not complete freshness acceptance. Phone: no. Watch: no. Live quota: no.

- **D4 — Add the offline Python/phone release gate.** **Overlap: refine the
  existing behavior-gate proposal; do not file separately.** F4; approximately
  1 agent hour for the initial valid-payload harness and gate wiring.

  **Work:** use Node's built-in VM/assert with mocked Pebble, localStorage,
  timers and XHR. Exercise the actual phone script with representative compact
  fixtures, check message keys against the manifest, and run the harness plus
  Python checks before release creation/publishing. Keep existing PBW checks.
  Leave malformed/overflow policy and C fixtures to the five-row proposal;
  delayed callbacks can extend this harness under request ordering.

  **Acceptance:** 0/1/5-row valid payloads, Fable identity and present/absent
  temperature map to the expected keys/values without devices or credentials.
  Existing Python tests pass on the declared CI Python. Demonstrate a failing
  assertion blocks the release dependency path in a disposable CI context,
  restore it, and retain successful CI evidence. If hosted execution is
  unavailable, record that acceptance gap rather than claim a verified gate.

  **Overlap/verification:** this slice does not satisfy every existing proposal
  criterion. Phone: no. Watch: no. Live quota: no. GitHub Actions: required for
  hosted gate evidence; existing settings/rendering device checks stay separate.

- **D5 — Remove unused collector helper generality.** Optional new candidate;
  F5; approximately 0.5–1 agent hour, after D1.

  **Work:** make the HTTP handler a directly named class and update repository
  call sites; narrow `iso_from_epoch` to numeric epoch formatting and remove
  its unused `None`/string branches. Keep its name, fractional-second support,
  datetime formatting and range-error behavior. Do not change the snapshot
  reader's accepted ISO timestamps or the typed server attributes.

  **Acceptance:** caller search confirms the removed inputs and factory
  customization are unused in this repository. Existing cooldown, HTTP, corrupt
  snapshot, out-of-range Retry-After and fractional HA-age tests pass; Ruff and
  ty remain clean. A small numeric formatting assertion preserves zero and
  fractional epochs. No change to routes, headers, disk format or emitted JSON.

  **Overlap/verification:** no open issue duplicates this cleanup; fold the
  handler portion into D1 if that avoids conflicting indentation changes.
  Phone: no. Watch: no. Live quota: no.

[collector]: ../../collector/pebble_quota.py
[tests]: ../../tests/test_pebble_quota.py
[Python suite]: ../../tests/test_pebble_quota.py
[phone]: ../../watchface/src/pkjs/index.js
[watch]: ../../watchface/src/c/watchface.c
[package]: ../../watchface/package.json
[workflow]: ../../.github/workflows/build.yml
[wscript]: ../../watchface/wscript
[project guide]: ../../README.md
[agent instructions]: ../../AGENTS.md
[collector guide]: ../collector.md
[watchface guide]: ../../watchface/README.md
[September architecture review]: ../2026-09-19-architecture-review-and-remediation-plan.md
[documentation review]: 2026-10-22-docs-review.md
[security review]: 2026-10-21-security-review.md
[historical spike]: ../../spikes/001-quota-collectors/README.md
[snapshot validation]: ../tasks/8-validate-windows-and-loaded-snapshots-before-publication.md
[Codex RPC handling]: ../tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md
[checker fixes]: ../tasks/19-fix-the-seven-ruff-and-four-ty-findings-and-document-both-checks.md
[behavior-gate proposal]: ../tasks/7-gate-releases-on-collector-and-phone-behavior-checks.md
[five-row contract proposal]: ../tasks/11-enforce-the-five-row-collector-phone-and-watch-contract.md
[freshness proposal]: ../tasks/9-carry-freshness-and-failure-status-through-to-watch-rendering.md
[request-ordering proposal]: ../tasks/14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.md
[settings recovery]: ../tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[Request ordering]: ../tasks/14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.md
[freshness]: ../tasks/9-carry-freshness-and-failure-status-through-to-watch-rendering.md
[five-row contract]: ../tasks/11-enforce-the-five-row-collector-phone-and-watch-contract.md
[operations proposal]: ../tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[temperature validation]: ../tasks/13-make-temperature-units-and-entity-age-explicit.md
[collector/build fixes]: ../tasks/16-fix-the-collector-and-build-findings-of-the-2026-10-21-security-review.md
[the existing backoff task]: ../tasks/2-back-off-on-http-429-from-claude-s-usage-endpoint-and-keep-the-last-re.md
[this task's record]: ../tasks/20-review-pebble-quota-s-architecture-for-deep-modules-and-over-engineeri.md
