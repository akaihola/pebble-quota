# Pebble Quota architecture review and remediation plan

Review date: 2026-09-19. Repository baseline: `c17db2ea1df0cb5056ff31027361d37f46ac3d57`. Task: `eac37fb2-a26f-4a78-8d09-a1f21831e6a8`. Session: `692ea452-1500-4f46-98fc-4b544ce7775f`. Confirmed current profile: Astra Medium, `gpt-6-astra`, medium effort. Confirmed workflow: Priority Kanban.

This is a completed review and proposed plan for user review. It does not authorize implementation, deployment, tracker edits, or new tasks. No repository files were changed. The working tree was clean at the beginning and end. No existing task plan was present on either read before saving this report.

## Architecture and scope

The project's purpose is a personal Pebble Time 2 quota display, backed by an already-authenticated private host. Its small architecture fits that purpose. Keep the standard-library Python service, one JSON snapshot, PebbleKit JS transport, and native C renderer. There is no evidence justifying a database, framework, message broker, provider plugin system, or service split.

Twenty tracked files were inventoried: nineteen text files, 1,966 lines in total, and one PNG. All source and text documentation were inspected, including hidden CI/configuration files. The screenshot was visually inspected. The root AGENTS.md and supplied shell guidance apply; no additional ancestor or nested AGENTS.md was found.

| Area | Files and responsibility | Assessment |
| --- | --- | --- |
| Collector/API | `collector/pebble_quota.py`, 420 lines | Provider adapters, normalization, pace calculation, snapshot publication, polling, public settings HTML, authenticated read API, CLI |
| Phone | `watchface/src/pkjs/index.js`, 88 lines | Local settings, HTTPS quota request, JSON-to-AppMessage mapping, configuration webview, 15-minute refresh |
| Watch | `watchface/src/c/watchface.c`, 393 lines | App lifecycle, minute clock/calendar, quota gauges, five-row in-memory state, initial sync request |
| Contract/build | `watchface/package.json`, `wscript`, `Makefile`, `shell.nix` | Emery-only app identity/message keys, SDK compilation/bundling, compiler selection, emulator libraries |
| Tests | `tests/test_pebble_quota.py`, 334 lines | 24 Python tests covering pace, compact representation, selected Claude payloads, snapshot writes, HTTP authentication/config page, temperature |
| CI/releases | `.github/workflows/build.yml`, `release-please-config.json`, `.release-please-manifest.json` | PBW build/metadata checks/artifact; release PR/tag and upload flow |
| Product/operations docs | root and watchface READMEs, screenshot | API outline, host assumptions, installation, build/emulator instructions, release process |
| Investigation/design record | `spikes/001-quota-collectors/README.md`, `probe.py` | Historical validation and duplicated prototype collectors; no separate ADR collection |
| Work tracking/guidance | `TASKS.md`, `docs/tasks/1-fix-codex-one-percent.md`, `AGENTS.md` | One open issue, completed settings item, maintenance/workflow rules |
| Ignore rules | `.gitignore` | Excludes local snapshots, credentials file convention, caches/build output |

### Boundaries, state, and deployment

1.  `main()`, collector lines 379–420, exposes `collect` and `serve`. Defaults are loopback port 8765, relative `latest.json`, and 300 seconds between refresh-loop waits. Serve requires `PEBBLE_QUOTA_TOKEN`; refresh interval must be positive.
2.  `collect_claude()`, lines 105–133, reads the user's local Claude credential file and calls the undocumented OAuth usage endpoint with a 15-second request timeout. It prefers `limits[]`, otherwise reads legacy fields.
3.  `collect_codex()`, lines 136–191, launches `codex app-server --stdio`, initializes JSON-RPC, reads rate limits, labels by duration, and terminates the subprocess. A daemon reader feeds a queue; a 15-second deadline bounds response waiting.
4.  `collect_temperature()`, lines 194–217, optionally uses `HASS_TOKEN` and `HASS_SERVER`, defaulting to localhost:8123 and a hardcoded weather entity. It assumes Celsius.
5.  `collect_all()` calls providers sequentially and records per-provider exceptions. `refresh_snapshot()` retains the previous whole snapshot on total failure, otherwise writes a replacement via a temporary file and rename. There is no history/database. The fixed temporary filename assumes one writer.
6.  A background refresh thread runs independently of the threaded HTTP read server. Steady-state requests read the snapshot rather than contacting providers. Startup tries a collection before opening the HTTP listener. Provider work can add roughly 35 seconds plus process cleanup to a cycle under timeout conditions; the loop waits another 300 seconds after work. These are control-flow bounds for ordinary timeout cases, not measured production latency guarantees.
7.  `make_handler()`, lines 340–376, serves unauthenticated static `/config` and exact-bearer-authenticated `/v1/watch`. It emits compact JSON, recalculating pace at request time, and suppresses access logging. Missing/unreadable/malformed snapshots return 503. TLS and tailnet access control are outside this process.
8.  Phone `refresh()` requests quota with a 15-second XHR timeout. `sendQuota()` takes the first five rows and maps fields to message keys. Ready, watch requests, and configuration changes can all initiate fetches.
9.  Watch `inbox_received()` replaces in-memory row state. `canvas_update()` renders the clock, noon-anchored calendar, bars and collection age. The watch recomputes elapsed markers every minute but uses transmitted pace colors. There is no watch persistence; reopening starts with empty rows.
10.  Settings live in phone localStorage. The existing token is also sent in the configuration URL query. Provider credentials stay on the collector host; the phone receives only the separate service token and compact quota data.
11.  README describes a continuously running `pebble-quota.service` and private Tailscale HTTPS endpoint. Neither service definition nor proxy/ACL configuration is in this repository. This is a documented deployment assumption, not verified live state.
12.  CI pins Pebble tool/SDK versions and checks PBW metadata. Release Please follows a successful build on main; publish downloads that run's artifact and checks version/tag agreement before uploading. Python collector deployment is manual/outside this pipeline.

The existing separation of provider credentials from the phone is useful. Atomic snapshot replacement, loopback binding, explicit bearer authentication, optional temperature, absence of runtime Python/npm dependencies, and a constrained display are sound choices for this scale.

## Evidence and verification

-   Ran `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: all 24 tests passed on Python 3.14.7. Initial sandbox execution passed 22 and could not create sockets for two HTTP tests. An approved rerun outside the sandbox passed all 24 with temporary loopback servers.
-   Ran `node --check watchface/src/pkjs/index.js`: passed.
-   Ran isolated Python checks with synthetic data and mocked subprocesses. Confirmed low-percentage conversion, unusable snapshot replacement, malformed-window failure propagation, RPC error suppression, partial-provider row disappearance, and stale-snapshot pace evolution.
-   Ran the unmodified phone script in Node's VM with mocked Pebble/localStorage APIs. Confirmed token query inclusion, acceptance of an unknown protocol version, and silent truncation of six rows to five.
-   Attempted `make clean build` in a copied watchface directory under `/tmp`. Pebble CLI failed during clean before compilation because it tried to write `pending_analytics.json` and `settings.json` under the read-only SDK directory. This is an environment limitation, not a demonstrated build defect. No SDK settings were changed.
-   Read recent Git history, including the tracker maintenance merge and completed-settings correction. No tracker statuses, task documents, branches, or commits were changed.
-   No real provider credentials, live provider calls, production snapshots, deployment configuration, or phone/watch sessions were inspected. No release was triggered. Source-linked conclusions below are about this revision.

## Prioritized findings

P1 means a high-value correctness or trust-boundary fix for the existing product, not a claimed production incident. P2 means a reliability or maintainability improvement with a narrower or less frequent trigger. Effort is relative: small is a focused change, medium crosses a boundary or requires several tests. Risk describes remediation risk.

| Rank / finding | Priority and classification | Impact and likelihood | Effort / change risk | Dependencies |
| --- | --- | --- | --- | --- |
| F1. Ambiguous percentage units | P1, confirmed defect, partly tracked | Wrong usage and pace at ordinary low usage; deterministic at 1% | Small / low | Existing issue 1 |
| F2. Invalid data can replace good state or break all quota delivery | P1, confirmed defect | One bad window can return 503 for both providers; payload drift is plausible | Medium / medium | Explicit units from F1 |
| F3. Failure/freshness semantics can mislead the display | P1, confirmed behavior with product-policy gap | Outages remove rows silently or keep expired data looking usable; outages are normal | Medium / medium | Valid snapshot contract from F2 |
| F4. Configuration exposes token in URL and can strand recovery | P1 for token handling; P2 for recovery, confirmed construction and failure path, exposure risk | Token reaches URL surfaces; a bad/unreachable endpoint also hosts its own repair UI | Small–medium / medium | Independent of quota fixes |
| F5. Behavioral checks are absent from CI | P1 enabling gap, confirmed | All merges/releases can pass with collector regressions; current tests also miss critical boundaries | Small initially / low | None; extend alongside fixes |
| F6. Codex RPC errors are accepted as empty success | P2, confirmed defect | Authentication/protocol failures lose useful diagnostics; possible on CLI changes/outages | Small / low–medium | F2 error conventions |
| F7. Five-row wire contract lacks selection and validation policy | P2, confirmed truncation; expanded-payload impact conditional | Extra Claude windows can evict Codex rows; malformed/version-mismatched data reaches watch | Medium / medium | F2 and F3; preserve compatibility |
| F8. Operations/build/config documentation is incomplete or inaccurate | P2, confirmed documentation gaps | Recovery and new-host installation rely on undocumented host state | Small–medium / low | Update as each behavior is settled |

### F1. Percentage inference corrupts legitimate provider values

Evidence: `collector/pebble_quota.py:48–52`, `fraction()`, divides by 100 only above 1. Calls at lines 98, 129, and 180 apply it to Claude `percent`, legacy `utilization`, and Codex `usedPercent`. Synthetic checks returned `fraction(0.5) == 0.5`, `fraction(1) == 1.0`, and `fraction(2) == 0.02`. A percentage of 1 becomes 100% on the watch through `compact_watch()` line 260; 0.5 becomes 50%.

Codex's case is already documented in `docs/tasks/1-fix-codex-one-percent.md:7–25`. The Claude percentage path shares the deterministic flaw for percentage-valued input; no fresh live Claude contract was checked. Confirm its units with a redacted representative payload rather than preserving a magnitude heuristic.

Existing Claude tests use 5, 40, and 55, so they miss the boundary, `tests/test_pebble_quota.py:280–331`. The prototype duplicates the heuristic at `spikes/001-quota-collectors/probe.py:26–30`.

### F2. Snapshot validity is tested as dictionary presence

Evidence: `has_quota_data()`, collector lines 279–281, accepts any nonempty `windows`. `refresh_snapshot()`, lines 284–291, then overwrites a known-good snapshot. The existing successful-write fixture even uses `{"used": 1}`, which cannot produce a compact row, tests lines 77–109.

Reproductions:

-   A window containing only `used` replaced a good snapshot and produced a new timestamp with `q: []`.
-   A bad reset string or NaN usage in Claude plus a valid Codex window passed `has_quota_data()` but raised ValueError in `compact_watch()`.
-   The HTTP handler catches that whole-response exception and returns 503, collector lines 360–365. Thus one provider's invalid data defeats the intended exception isolation in `collect_all()`.

Validation is deferred until HTTP serialization. Missing values are skipped, but wrong shapes, invalid timestamps, non-finite numbers, negative durations, and wire-size constraints have no consistent boundary treatment. This is an availability and correctness defect, not evidence of remote code execution.

### F3. Collection success, delivery success, and data freshness are conflated

Evidence: collector lines 220–239 stamp a whole attempt, lines 284–291 replace on partial success, and `compact_watch()` lines 242–265 omit service errors. A synthetic partial outage replaced both-provider state with only Codex and a newer timestamp. The watch therefore loses Claude rows with no explicit provider-unavailable indication.

Total failure preserves the previous snapshot indefinitely. The API recalculates its pace against the current time. With a fixed 20% sample at the start of a five-hour window, the synthetic check changed `p` from -20 to +80 at reset and kept +80 after reset, without new usage data. On the watch, `canvas_update()` lines 264–269 does show collection age, which mitigates the problem, but no threshold or expired-window presentation changes the normal gauges.

Separately, `elapsed_percent()`, watch lines 42–46, advances the marker each redraw, while `draw_single_gauge()` lines 195–205 uses a pace color stored from the last phone message. Colors and marker can disagree during the normal 15-minute phone interval. Old temperature can also remain when the whole snapshot is retained, qualifying README's blanket omission-on-HA-outage wording.

This requires a small explicit freshness policy. It does not require keeping unlimited history or inventing usage after a reset.

### F4. Configuration carries secrets in URLs and depends on the endpoint being repaired

Evidence: phone `configUrl()`, lines 58–62, puts the existing bearer token in `?token=`; `showConfiguration`, lines 65–67, opens that URL. Node reproduction with a synthetic token confirmed its presence. The collector reads it from `location.search`, lines 322–328. The HTTP request target therefore contains the token. Browser/webview history and intermediaries that record request targets may retain it. The built-in server disables logging, and no actual intermediary leak was observed.

`webviewclosed`, phone lines 69–78, accepts arbitrary nonempty endpoint/token values without URL policy. HTTP endpoints can send the service token without transport encryption. Once an unreachable or mistyped endpoint is saved, `configUrl()` uses the same endpoint to locate the repair page. Recovery may require reinstalling/resetting local storage. README claims the settings page is “always reachable,” watchface lines 66–71, which is false during outages or invalid configuration.

The unauthenticated static config page is intentional and need not become authenticated. The service token authorizes quota reads, not provider account access; keep this distinction in risk assessments.

### F5. CI verifies packaging but not behavior

Evidence: `.github/workflows/build.yml:12–71` installs the build tool, builds PBW, and validates metadata. There is no Python test invocation anywhere in the workflow. Release Please depends only on build at lines 73–89. Tests contain no Codex adapter tests, JS tests, or committed watch test harness. The historical calendar harness claim appears at `watchface/README.md:30–35` without its harness in the inventory.

A successful CI build does not establish collector correctness or runtime protocol behavior. Existing Python tests passing alongside F1/F2/F6 reproductions demonstrates specific coverage gaps, rather than a speculative concern about coverage percentages.

### F6. JSON-RPC failure handling loses the cause

Evidence: `collect_codex()`, collector lines 166–184, recognizes response IDs but never checks `error`. For id 2, it defaults missing result to an empty dictionary and returns empty windows. A mocked `{"id":2,"error":...}` returned `{"service":"codex","windows":{}}`. Errors during initialize likewise trigger the next request.

Queue timeout raises `queue.Empty` before the intended descriptive TimeoutError in the usual no-output case. EOF is not signaled explicitly. The kill fallback at lines 186–191 does not wait again or explicitly close pipes. These latter points are lifecycle risks, not a measured production leak. Error classification and process cleanup should be tested without requiring authenticated Codex.

### F7. The compact protocol exceeds what the watch can represent

Evidence: collector accepts arbitrary weekly-scoped names, lines 89–94, and emits all rows with Claude before Codex, lines 246–264. Phone `sendQuota()`, lines 11–23, silently takes five. A six-row synthetic response forwarded only five. The C row label has eight bytes including terminator, watch lines 24–31; non-Fable scoped names such as `7d (model)` can truncate.

The `v` field is emitted but ignored by the phone. A synthetic version 99 payload was accepted. `inbox_received()`, watch lines 313–346, bounds row count and checks string type, but integer tuples are read without type/length validation and missing strings can leave old labels. Treat this as weak defense at the transport boundary, not a demonstrated exploit.

The combined Claude/Fable gauge also assumes equal reset times and durations without checking them, watch lines 208–223 and 280–290. A mismatch would draw one marker for two distinct windows. Actual current matching resets were not verified.

### F8. Documented operation cannot be reconstructed from repository contents alone

Evidence:

-   `README.md:78–84` describes the running service and tailnet exposure, but no unit/proxy definitions or runbook are tracked.
-   CLI output path is relative, collector line 382; deployment must define working directory or use an absolute path. Credential user/HOME, Codex PATH/version, writable state directory, restart policy, token provisioning/rotation, and recovery are not specified.
-   `watchface/README.md:43` claims SDK 4.17; CI pins 4.33.1 and Makefile selects `SDKs/current`, not a specific version.
-   `watchface/README.md:69–70` describes `<endpoint>/config`, but code strips `/v1/watch` to produce origin/base `/config`.
-   `README.md:28–36` omits `v`, `at`, `q`, the F service code, row limits, timestamp/freshness policy, and which fields are top-level.
-   Collector refresh is about five minutes plus collection time; phone refresh is fifteen minutes, phone line 5 and lines 81–84. Only the former is described.
-   `TASKS.md:14` says settings “survive reinstalls.” localStorage use proves phone-side persistence while retained by the app, not all reinstall behaviors. Verify physical-device behavior and qualify documentation without reopening the completed feature.
-   The spike is explicitly a prototype, but still presents a runnable validated collector with obsolete parsing. Mark it historical rather than maintaining a second production implementation.

## Ordered remediation plan

The sequence starts with the already-tracked deterministic user-visible bug and the independent token issue, establishes automated checks, then repairs snapshot and freshness semantics. Contract enforcement follows those decisions so it does not encode today's failure behavior. Documentation is corrected in each step, with a final operational pass. Each step is a proposed change set, not a new task or authorization to execute.

### Step 1. Complete existing issue 1 with explicit provider units

Addresses F1. Reuse `docs/tasks/1-fix-codex-one-percent.md` and its existing number; do not create a duplicate Codex plan.

Changes: make percent-to-fraction conversion explicit in the Codex adapter; apply the same documented rule to confirmed percentage-valued Claude fields. Add boundary regression cases at adapter level and compact-output assertions in `tests/test_pebble_quota.py`. Update the existing task description only when implementation is authorized to cover the shared cause, preserving its current acceptance criteria. Mark the prototype's duplicated normalization as historical or point readers to the production collector.

Prerequisites: confirm the legacy Claude field's units with redacted evidence before changing that adapter. Codex's existing 0/1/100 acceptance criteria are already established.

Acceptance and verification: 0, 0.5, 1, 2, and 100 percent normalize to 0, .005, .01, .02, and 1 where fractional percentages are allowed. Compact output for 1% is `u:1`; pace uses .01. Test missing values separately. Run all collector tests. Retain the task's live snapshot comparison as an operator verification, not a requirement to expose credentials in CI.

Benefit: fixes a common, dramatic display error with a small change. No persisted format change. Recollect after rollout so an old wrongly normalized snapshot does not remain. Roll back the code if necessary; never try to infer and rewrite historical fractions by magnitude.

### Step 2. Remove token query transport and provide settings recovery

Addresses F4 and associated F8 inaccuracies. Independent of Step 1.

Changes: update `configUrl()`, config HTML parsing, and settings validation together. At minimum, stop prefilling the existing token into an HTTP query; allow a blank token field to mean “keep current token” for an unchanged endpoint and require deliberate token entry when changing origins. If prefill is retained, use a verified client-only channel and document that the page itself remains trusted. Validate HTTPS endpoint shape before storage, with an explicit local-development exception if required. Do not silently reuse a token for a different host. Provide a configuration/reset route whose bootstrap location does not depend on the potentially broken stored endpoint, and document recovery when the bootstrap service itself is unavailable.

Acceptance and verification: mocked `openURL` contains no token in path/query; captured HTTP request targets contain no token. Test cancel, malformed settings, blank fields, invalid URL/scheme, origin changes, and recovery from an unreachable saved endpoint. Test a physical phone save/reopen flow and reinstall persistence separately. Keep `/config` usable without bearer authentication.

Benefit: narrows secret exposure and avoids configuration lockout. Release collector config HTML support before a phone bundle that depends on it. Preserve existing valid localStorage values. If URL-prefill compatibility is needed temporarily, bound and remove it. Token rotation is appropriate if actual URL logs/history exposure is established or as an operator precaution; it is not evidence that a compromise occurred.

### Step 3. Make behavior checks a release prerequisite

Addresses F5. No prerequisites; can be prepared alongside Steps 1–2.

Changes: add the existing unittest command to CI on PRs and main, either before build or in a test job that release creation depends on. Add a small Node test runner using built-in VM/assert facilities for config and JSON/AppMessage behavior. Add regression tests as part of each subsequent fix. Preserve PBW archive/identity/version checks.

Acceptance and verification: a deliberate failing Python assertion in a temporary branch prevents the release job from running; the restored suite passes. JS settings and protocol fixtures execute without Pebble hardware. CI uses a declared Python version compatible with the collector and records it. Avoid installing a testing framework solely for these scripts.

Benefit: prevents repeated regressions while remaining cheap. No runtime migration. Roll back a broken CI invocation independently, but retain the test gate. Do not make deployment depend on production credentials.

### Step 4. Validate provider windows before publishing and isolate failures per window

Addresses F2. Depends on Step 1's unit rules; use Step 3's checks.

Changes: introduce one small normalized-window validation boundary inside the collector, reused by collection/publication. Validate object shape, finite numeric usage with an explicit policy for values outside 0–100%, valid reset timestamp, positive bounded duration, and values representable by the watch. Reject malformed windows individually; preserve valid windows from the same or other provider. Define usable data using successfully validated rows, not dictionary truthiness. Retain the previous good snapshot when a refresh yields no usable rows. Keep atomic replacement.

Update successful-refresh fixtures to contain real valid windows. Update API documentation with validation and unavailable-data semantics. Keep the HTTP layer a serializer of validated state while still handling damaged on-disk files gracefully.

Acceptance and verification: missing fields, NaN/infinity, strings in numeric fields, bad timestamps, zero/negative duration, malformed scope, and wrong container types cannot replace good data. One invalid Claude window plus valid Codex still returns valid quota data. An invalid new snapshot cannot turn a good state into empty success. Test startup without a snapshot, corrupt snapshot, disk-write failure, and total failure. Assert old state survives unsuccessful publication.

Benefit: protects the central availability guarantee. No schema migration is required if normalized fields stay the same. Treat old snapshots as untrusted inputs on load; preserve a backup or recollect rather than guessing repairs. Roll back with the previous valid snapshot and code if needed.

### Step 5. Make stale, failed, and expired data explicit through to the watch

Addresses F3 and part of F7. Depends on Step 4.

Changes: choose and document a bounded freshness policy based on the actual 5-minute collector and 15-minute phone cadence. Preserve last-good provider rows during partial failures only with their own original timestamps and an explicit stale/error status, or clearly display that provider as unavailable. Never give retained provider data a new successful timestamp. After a reset passes without a fresh observation, show stale/unknown rather than interpreting old usage as the new window. Apply the same policy to temperature.

Add compact status/age fields and message keys only as needed. Update phone mapping and watch rendering. For fresh data, compute pace color and marker from the same current elapsed calculation; stale rendering must override any reassuring color. Add concise failure status rather than raw provider exception strings on the watch. Keep useful diagnostics on the host without secrets.

Acceptance and verification: end-to-end synthetic sequences cover both healthy, one failed, both failed, recovery, old snapshot at startup, reset crossing, phone offline, future timestamps, and absent temperature. Missing-provider rows cannot silently look like a full successful refresh. Clock/calendar continue working. Marker/color agree for fresh data at chosen boundaries. Reconnection clears stale state only after a valid update.

Benefit: the display communicates how much its quota advice can be trusted. Deploy additive API fields first, then the phone/watch consumer; old clients must continue to receive existing required fields during transition. Preserve timestamp meaning during rollback. Do not silently change v1 field meanings or infer reset usage.

### Step 6. Make the Codex subprocess adapter fail clearly and clean up deterministically

Addresses F6. Depends on Step 4's error conventions; can proceed alongside Step 5.

Changes: check JSON-RPC `error` and result shape for initialize and rate-limit responses. Distinguish timeout, premature EOF, invalid JSON, and valid no-window responses. Ensure terminate/kill is followed by reaping and pipe cleanup. Preserve duration-based labeling. Keep the existing small subprocess approach unless measurements show a need to change it.

Acceptance and verification: fake app-server cases cover success, notifications before response, initialization error, rate-limit error, EOF, no response, malformed JSON, and forced-kill cleanup. Failures record actionable sanitized errors and do not erase the other provider's valid data. Tests do not call authenticated Codex. Record the tested CLI version in operations docs.

Benefit: faster diagnosis of a likely integration failure without adding a framework. No wire migration. Rollback is a collector code change; keep fixtures to expose incompatibility with another CLI version.

### Step 7. Enforce the bounded collector-to-watch contract

Addresses F7 and remaining display assumptions. Depends on Steps 4–5.

Changes: document a stable priority/selection rule for five rows so core Claude/Codex windows cannot be displaced by extra scoped rows. Keep display identity separate from arbitrary provider display names where necessary. Validate the compact version, required fields, finite integer ranges, and row strings in phone code before sending. Reject a malformed update atomically rather than clearing or mixing watch state. In C, check tuple type/length for numeric values and reset/replace rows coherently. Only combine Claude/Fable gauges when reset time and duration match; otherwise render separate rows under the capacity policy.

Add a minimal transport fixture shared conceptually across Python, JS and C tests, without a code generator or generic schema framework. A small host C harness or a stubbed Pebble receive/render boundary is sufficient.

Acceptance and verification: test 0, 1, 5, and 6+ rows; additional scoped models; long names; unsupported versions; missing/wrong tuple types; missing fields; mismatched resets. Valid five-row messages fit the 2048-byte inbox. Core providers remain visible under overflow. Verify all message keys against package.json and inspect Emery screenshots for five unpaired rows and stale status.

Benefit: keeps provider expansion from silently changing the display. Prefer additive compatible fields; if the protocol must break, version it and define a clear unsupported-version state. Roll back collector and PBW as a compatible pair if required.

### Step 8. Document reproducible operation and reconcile release/build assumptions

Addresses F8 and lower-priority operational concerns. Finish after preceding behavior choices; simple factual corrections can accompany earlier steps.

Changes: expand the two READMEs with the full compact schema, sample redacted payload, default CLI settings, collection versus phone cadence, failure policy, endpoint/config URL distinction, credential ownership, state directory, token lifecycle, and recovery procedure. Include a minimal service example or a precise link to the authoritative host configuration, with user, working directory, PATH, restart behavior, and loopback/TLS boundary. Declare single-writer operation or make temporary snapshot filenames safe for concurrent manual collection. Document local SDK/tool installation consistent with CI and the Makefile's active SDK selection.

Mark the spike as historical. Commit the calendar test harness if its ongoing guarantee is retained; otherwise describe it as historical manual verification. Verify version/release history before changing the release manifest.

Acceptance and verification: a reviewer can perform an offline/mock startup, locate logs/state, explain how to refresh credentials, recover stale data, rotate the service token, and rebuild a PBW using the documented setup. Auth/no-auth/error-path tests match the documented API. In an authorized staging environment, verify proxy routing for both endpoints and that loopback is not accidentally exposed publicly. Verify PBW version/tag and one release-upload retry path without publishing a production release.

Benefit: makes a personal deployment recoverable without changing its scale. No production deployment is part of this review. Back up actual service/proxy configuration before any later operational change and keep the prior PBW/collector revision available. Documentation changes need no migration.

## Lower-priority findings and verification backlog

These do not justify delaying the main fixes.

-   **Concurrent refresh writers:** `write_snapshot()`, collector lines 272–276, uses one fixed `.tmp` path. A manual `collect` alongside `serve` can race. No concurrent production writers were observed. Document one writer; use a unique same-directory temporary file if overlapping commands are supported. Test two writers before claiming concurrency support.
-   **Temperature units:** `collect_temperature()`, lines 214–217, assumes the entity's number is Celsius and ignores unit metadata. Correct for the documented deployment only if its HA unit system is Celsius. Verify or convert/reject explicitly; test Fahrenheit and stale entity data before supporting other hosts.
-   **Phone request ordering/retry:** `refresh()` has no in-flight guard or freshness comparison, and AppMessage failure only logs, phone lines 24–55 and 81–88. Overlapping ready/watch/config requests can finish out of order; settings changes may allow an older endpoint response to overwrite a newer one. Reproduce with delayed mocked XHRs; then add only the needed in-flight or generation guard and bounded retry. No observed production incident.
-   **HTTP scope:** `ThreadingHTTPServer` has no application connection limits, and 503 responses include exception text, collector lines 302–304 and 363–365. Keep private loopback/proxy deployment explicit. Sanitize errors when touching diagnostics; do not introduce a full web framework or internet-facing service architecture without a new requirement.
-   **Release state/retries:** package version is 0.2.0 while the Release Please manifest records 0.1.0. That is a confirmed mismatch, not sufficient evidence of broken releases. Check actual tags/release PR history before altering it. Upload at workflow line 118 is not written as an idempotent retry; test an interrupted publish and document recovery. No online release state was checked.
-   **Calendar portability:** the noon anchor and fixed 86,400-second offsets are reasonable for the current locale's ordinary DST shifts. Preserve tests for month/year/leap/DST boundaries; do not rewrite calendar logic based on hypothetical timezone anomalies.
-   **Persistence/performance:** no watch cache means a face restart while offline shows no quotas. Decide whether that behavior matters before adding persistence. At five rows, source inspection provides no evidence of a rendering or file-read bottleneck. Provider latency, phone interval, and freshness handling matter more than optimizing loops. No battery or runtime benchmarks were performed.

## Backlog reconciliation and completion boundary

`TASKS.md` has exactly one open item, issue 1, and one completed settings item. The issue-1 description and backlog agree. F1 overlaps that existing issue; extend its implementation scope only as justified by the shared conversion bug. This report's F identifiers are review references, not new task numbers.

The settings feature exists and its completed status is supported by code. F4 is follow-up hardening/recovery work, not grounds to undo the prior status correction. The “survive reinstalls” wording needs device verification, not an automatic status change. Git history includes `b571a70`, `064c13b`, and the baseline maintenance merge; that work was preserved. No other docs/tasks files or pending plans were found.

Once the user chooses implementation scope, reconcile these steps into the existing tracker under its maintenance rules, reuse issue 1, and add only genuinely distinct work. This review does not perform those edits or start that workflow.

The most valuable first actions are explicit percentage conversion, safe settings transport/recovery, and a CI behavior gate. Then protect valid snapshots and make freshness visible. Those changes address demonstrated failures while retaining the architecture that already fits the project.

Limitations: no successful C/PBW compilation in this environment, no emulator or physical-watch run, no live provider contract or account verification, no production service/proxy inspection, and no online CI/release-history audit. Synthetic checks prove the identified code paths, not their production frequency. The review and plan are complete and ready for user review; implementation remains unstarted.
