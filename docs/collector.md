# Collector reference

The standard-library [collector] provides `collect` and `serve`; see the
[quick start] for commands. Run from the repository root, or use an absolute
script path and output path. No Python packages are required beyond the standard
library; the source requires Python 3.10 or newer. See the [documentation recheck]
for the verification environment.

## Commands and settings

`collect` refreshes once, writes the full snapshot, and prints compact JSON to
stdout on success. It needs no service token. `serve` requires a nonempty
`PEBBLE_QUOTA_TOKEN`, binds the listener before starting collection, and refreshes
in a background thread. HTTP reads use the disk snapshot without calling
providers; a first request can return 503 before collection finishes.

| Option | Default | Meaning |
| --- | --- | --- |
| `--output` | `latest.json` | Snapshot path relative to the working directory; shared by reads and writes |
| `--host` | `127.0.0.1` | HTTP bind address for `serve` |
| `--port` | `8765` | HTTP port for `serve` |
| `--refresh-seconds` | `300` | Positive wait after each `serve` collection pass, also the minimum interval between a provider's recorded attempts |

The loop waits after work, so its cadence is collection time plus the configured
wait, not exactly five minutes. Persisted `last_attempt_at` values suppress
premature attempts after a restart. One-shot `collect` does not apply that
minimum interval, but does honor Claude's persisted 429 cooldown. Use one writer
per snapshot: atomic replacement prevents partial files, not lost updates from
concurrent collection processes.

| Environment | Use |
| --- | --- |
| `PEBBLE_QUOTA_TOKEN` | Bearer token for quota reads; required by `serve` |
| `HASS_TOKEN` | Optional Home Assistant long-lived token; absence omits temperature |
| `HASS_SERVER` | Home Assistant base URL, default `http://localhost:8123` |
| `HOME` | Determines the Claude credential location and is passed to Codex |
| `PATH`, `CODEX_HOME` | Select the Codex executable and, when set, its home |

Claude reads the collector user's local OAuth credentials (`collect_claude`)
and calls the undocumented OAuth usage endpoint. Codex runs
`codex app-server --stdio` and calls `account/rateLimits/read`. Its subprocess
receives an allowlist of home/path, terminal, locale and proxy settings, plus
`SHELL=/bin/bash`; service and Home Assistant tokens are not forwarded. Claude
and Home Assistant HTTP requests refuse redirects. Provider HTTP timeouts are
15 seconds for Claude and 5 seconds for Home Assistant.

## HTTP and compact payload

```text
GET /v1/watch
Authorization: Bearer <token>

GET /config
```

`/config` serves the static phone settings page without authentication so a fresh
install can configure its service token. Only watchface versions up to 0.2.0 open
it; from 0.3.0 the page ships in the phone script. See [phone settings] for
storage and recovery limitations. `/v1/watch` requires an exact bearer token
(401 otherwise); unknown paths return 404. An unreadable, corrupt, rowless or
invalidly timestamped snapshot returns 503 `Snapshot unavailable`. Valid rows
in partially damaged snapshots remain available. Both successful routes send
`Cache-Control: no-store`; the server suppresses access logging.

The compact payload has these top-level fields:

| Field | Meaning |
| --- | --- |
| `v` | Protocol version, currently `1`; the phone rejects any other value |
| `at` | Snapshot `collected_at` as integral Unix seconds; collection-pass time, not each provider's last success |
| `q` | Validated quota rows, at most five less one per provider in `n`; see [five gauge lines] |
| `n` | Optional service codes (`C`, `X`) of providers without rows, for example `"X"` after a failed Codex read |
| `t` | Optional outside temperature in integer tenths of Celsius, read in the pass `at` |

Each row contains:

| Field | Meaning |
| --- | --- |
| `s` | One-letter wire code: `C` for Claude, `F` for Claude's Fable scope, `X` for Codex |
| `w` | Window label, usually `5h` or `7d`; other Codex durations use `<minutes>m` |
| `u` | Integer percentage used, rounded with Python's `round` |
| `r` | Reset time as integral Unix seconds |
| `d` | Window duration in seconds |
| `p` | Rounded `(elapsed_fraction - used_fraction) * 100`; positive means unused quota is ahead of constant-use pace, negative means usage is ahead of pace |
| `o` | Collection-pass time of the provider's last successful reading, as integral Unix seconds: the service's `last_success_at`, or `at` when that is missing |
| `e` | Optional `1`: the provider's latest attempt failed and the row is its last good reading, from `o` |

`n`, `o` and `e` were added within version 1; every older field keeps its
meaning. `e` and `n` carry no error text: diagnostics stay in the snapshot.

Synthetic example at the start of a five-hour window:

```json
{"v":1,"at":1800000000,"q":[{"s":"C","w":"5h","u":20,"r":1800018000,"d":18000,"p":-20,"o":1800000000}],"n":"X","t":215}
```

### Five gauge lines

The watch has room for five gauge lines. Each provider listed in `n` takes one
for its `unavailable` line, and rows fill the rest in this priority:

1. core (unscoped) windows before scoped extras;
2. Claude before Codex;
3. shorter window first, then wire code, then window label.

Claude's adapters produce at most two core windows (5h and 7d) and Codex's at
most two (its primary and secondary windows), so every core window always gets
a line. Scoped extras, Fable today and any scope added later, fill the lines
left over in a stable order. The chosen rows are sent in display order:
Claude, its scoped extras, then Codex, each by duration. The order no longer
depends on the snapshot's mapping order, so `collect` output and HTTP reads
agree.

### Wire identity

A row's identity on the wire is its one-letter code `s` and its window `w` of
one to seven printable ASCII characters. Provider display names never cross the
wire. The snapshot keeps a scope's display name in its window label, for
example `7d (Fable)`, and a table in the [collector] maps each supported scope
to its code (`Fable` → `F`). A new scope needs only a new table entry; the
watch names known codes itself and shows an unknown code as its letter. Claude
labels with any other parenthesised scope are invalid, however short.

### Phone and watch validation

The phone checks the whole payload before it builds a message: `v` must be 1,
`at` an integer from 0 through 2147483647, `n` absent or up to three capital
letters, `t` absent or an integer from -2147483647 through 2147483647, and `q` an
array whose length plus the length of `n` is at most five. Each row needs `s`
(one capital letter), `w` (one to seven printable ASCII characters), `u` (0–100), `r`
(0–2147483647) and `d` (1–21,474,836) as integers. `o` may be absent or an
integer timestamp, and `e` absent, 0 or 1. The phone does not read `p`. Any
failure, including unparsable JSON, logs `Rejected quota data:` with the reason
and sends nothing, as a failed request does, so the watch keeps aging its last
valid rows until they turn stale.

The watch decodes each message into scratch space and replaces what it shows
only when the whole message is valid. Integers must be signed or unsigned
tuples of 1, 2 or 4 bytes within the phone's ranges, except `TEMP` also accepts
-2147483648. Strings obey the phone's text bounds and must contain a NUL
terminator within their declared bytes; a zero-byte tuple is invalid even for
an empty `UNAVAILABLE` string.
`COLLECTED_AT`, `ROW_COUNT`, `UNAVAILABLE` and all seven keys of every counted
row are required; `TEMP` is optional. A rejected message leaves the previous
display intact.

The largest valid message, five rows with seven-character windows and a
temperature, takes 437 bytes of the watch's 2,048-byte inbox.

## Snapshot validation and failures

The full snapshot contains `collected_at`, a `services` mapping for Claude and
Codex, and optional `temperature_c_tenths` / `temperature_error`. Service
`windows` map labels to `used_fraction`, `resets_at` and `duration_seconds`.
Scheduling and error fields remain in this file. Compact output derives only
`o`, `e` and `n` from them.

Claude's usage request includes `cedar_ember=1&skip_spend=1`. The snapshot's
`cedar_ember` block keeps only eligibility, the next grant ID and the grant
fields needed by [kandev-pacer] to plan banked resets. Other provider fields are
discarded. This lets the pacer share the collector's quota poll; grant metadata
stays outside compact phone/watch output. Missing grant metadata identifies an
older snapshot; an explicit empty block means no usable grants were reported.

Quota windows are validated individually on collection and every snapshot read:

- **Usage:** finite JSON numbers in `[0, 1]`; provider percentages in `[0, 100]`.
  Strings, booleans and out-of-range values are rejected, never clamped.
- **Reset:** nonnegative integral Unix seconds or timezone-aware ISO 8601,
  through `2147483647` seconds. ISO fractional seconds are truncated for the
  watch. Numeric strings and timestamps without timezones are rejected.
- **Duration:** integer seconds from 1 through 21,474,836, keeping the watch's
  duration-times-100 calculation within signed 32-bit range.
- **Labels:** a window of one to seven printable ASCII characters, plus for
  Claude an optional supported scope as in `7d (Fable)`; see [wire identity].
  The Claude adapter accepts only the supported unscoped windows and scopes;
  malformed or unsupported scopes are skipped.

Malformed containers and scheduling fields are discarded. Healthy providers
still run, and bad windows cannot suppress valid siblings. Writes use a unique
same-directory temporary file, created with mode 0600, and atomic replacement.
A write failure preserves the prior file; `serve` retains new scheduling state
in memory. Restart guarantees depend on disk writes succeeding.

Both providers record `last_success_at`, the pass time of their latest
successful reading. Codex has recorded it since the freshness change; older
snapshots lack it, and compact rows then fall back to `collected_at`.

Claude failures retain its last successful windows with `error`, `stale: true`,
`last_success_at` and `age_seconds`. Age counts from that successful reading;
`collected_at` describes the current pass when those retained rows are published.
Codex has no equivalent per-provider retention on a partial failure: a failed
Codex pass leaves `error` without `windows`. Snapshot readers such as kandev-pacer
rely on that, so the compact payload lists Codex in `n` instead, and the watch
shows it as unavailable.

If collection produces no usable rows, `refresh_snapshot` calls the pure
`merge_unavailable_snapshot`, which retains prior validated quota, collection
time and temperature while merging service attempt/cooldown metadata and
marking retained services stale. `refresh_snapshot` writes that state, then
raises an unavailable-reading error. With no prior quota, the
scheduling-only snapshot is saved but is not a successful publication; HTTP
returns 503. Retained Claude rows count as usable, so both providers failing does
not necessarily enter this whole-snapshot fallback.

### Claude cooldown

HTTP 429 pauses Claude requests until a persisted `retry_at` deadline. Positive
`Retry-After` seconds or future HTTP dates take precedence; missing, zero,
invalid or expired values use 10, 20, 40, then 60 minutes between consecutive
429 attempts. Requests resume on the first refresh at or after the deadline.
Codex and temperature continue refreshing. Successful collection clears retry
state; a different failure also replaces the 429 fields. Repeated `collect`
commands and restarts share cooldown only when they use the same output file.

### Claude request journal

Each actual Claude usage request writes one stderr line with prefix
`claude attempt: ` followed by JSON. Fields are `provider` (`claude`),
`outcome` (`ok`, an integer HTTP error status, `parse_error` for unusable
windows, or a fixed error category such as `TimeoutError`, `URLError` or
`JSONDecodeError`), `attempt_at` (UTC request start), `last_success_at`
(the previous service value), `retry_at` (the resulting cooldown deadline),
and `retry_after`. Missing values are JSON `null`. Successful requests clear
`retry_at`; a non-429 error also clears it. The snapshot and cooldown rules
are unchanged. Scheduling state is written by the normal snapshot persistence;
its existing failure diagnostic still applies if a disk write fails.

`retry_after` contains only the response's Retry-After metadata: decimal seconds
are normalized, HTTP dates become ISO timestamps, and malformed values become
`invalid`. Other headers, credentials, URLs, bodies and provider fields never
enter these lines. Credential/preflight failures before HTTP starts produce no
request line. Parse failures after a response still count as requests.

A skipped pass writes `claude skip: ` with the same JSON fields and outcome
`refresh_interval` or `retry_at`, at most once per refresh pass. Its `attempt_at`
is the pass time; no HTTP request took place. Skips never enter request counts.

Daily counts by request outcome for the previous calendar day (local timezone);
for a system-unit install, drop `--user`:

```bash
journalctl --user -u pebble-quota.service --since yesterday --until today -o cat | python3 -c 'import collections,json,sys; print(dict(collections.Counter(str(json.loads(line.removeprefix("claude attempt: "))["outcome"]) for line in sys.stdin if line.startswith("claude attempt: "))))'
```

### Codex diagnostics

RPC failures use fixed diagnostics naming the stage (`initialize` or
`rate limits`) and cause: RPC error, response timeout, unexpected EOF, invalid
JSON, invalid response/result, or pipe failure. RPC errors call for checking
CLI login and protocol compatibility. Raw RPC messages, data and stdout are not
published. Notifications do not extend the single 15-second response deadline
covering both stages. The child is terminated, killed after a two-second exit
grace if needed, reaped and its pipes closed on success and failure.

Legitimate empty window sets report `Codex rate limits: no quota windows`;
malformed results fail collection, while valid sibling windows survive bad ones.
Other provider/snapshot errors use fixed categories such as `HTTPError`, not
exception messages, URLs, response bodies or credentials.

Installed Codex CLI compatibility remains **unverified by this review**. Tests use
fake app-servers with initialize's `userAgent` result and both wrapped
`rateLimits` and legacy direct window results. No installed CLI version was
verified in this check. Deployment/restart evidence belongs to the
[Codex adapter task].

## Temperature

Temperature is a best-effort read of Home Assistant's `weather.forecast_koti`
(the documented met.no entity for Koivusyrjä). Only `attributes.temperature_unit`
values `°C` and `°F` are accepted; Fahrenheit uses `(F - 32) * 5 / 9`. Both are
rounded to integer tenths of Celsius with Python's `round`. Missing/unknown
units, missing/nonnumeric/nonfinite values and unknown/unavailable entities
produce no temperature.

Freshness requires an ISO 8601 `last_updated` with an explicit timezone, aged
from zero through 7,200 seconds at collection time. Missing, malformed,
timezone-free, future or older timestamps produce no temperature. This allows
an hourly weather update plus collection delay; entity age does not prove
when the weather was observed. Home Assistant's [state timestamp semantics]
mean unchanged weather can age out, while an unrelated attribute change can
refresh `last_updated`. There is no fallback to `last_changed`, `last_reported`
or collection time.

`collect_all` omits rejected temperature; HTTP/network/JSON failures record
`temperature_error` without removing quota. Whole-snapshot fallback retains old
temperature together with the old `collected_at`, so `at` always names the pass
that read the temperature. The watch applies the display freshness policy below
to it.

## Display freshness policy

The watch judges every row against its own clock, so rows keep aging while the
phone is offline. The bound covers the real cadences: the collector waits 300
seconds after each pass of up to about 37 seconds of work, and the phone polls
every 15 minutes with a 15-second timeout. A healthy reading therefore reaches
the watch within about 21 minutes.

- **Fresh:** a row's reading (`o`) is at most 25 minutes old, its provider's
  latest attempt did not fail, and its window has not reset. Its color comes
  from the watch's current elapsed percentage minus `u`, the same elapsed value
  that places the marker: green at zero or above, yellow from -10 through -1,
  red below -10. The watch ignores `p`.
- **Stale:** the reading is older than 25 minutes, `e` is set, or `o` is more
  than 5 minutes ahead of the watch clock. The used part turns dark gray and
  the title row shows `stale 12m` (or hours, then days) or `clock skew`.
  Readings up to 5 minutes ahead count as age zero.
- **Reset:** once the watch clock reaches `r`, the old usage belongs to an
  ended window. The bar shows an empty dark track, no marker, and `reset ?`.
- **Unavailable:** each provider in `n` gets its own line showing
  `unavailable` over an empty dark track.
- **Temperature:** hidden when the message omits `t`, or when `at` is older
  than 25 minutes or more than 5 minutes ahead. Home Assistant's two-hour
  entity-age limit above still applies on the host.

Failed phone requests send nothing, so the watch keeps aging its last rows. See
[phone response ordering] for superseded requests, the bounded timestamp guard
and deferred AppMessage retries. The first gauge shows `updated Nm ago`, the
age of `at`, only while that gauge is fresh (`phone sync pending` when `at` is
zero). The collector keeps timestamps as recorded and never rewrites them to
the current time. `p` keeps its version 1 meaning for old watches, which still
color from it and show expired windows; only the new watch bundle applies this
policy. The [watchface guide] describes rendering and phone refresh triggers.

## Rollout and rollback

Deploy the collector first, then install the watch bundle (its phone script and
watch app ship together). Old phone scripts read only the older fields, so they
keep working against the new API. Snapshot readers see one addition, Codex's
`last_success_at`.

To roll back, reinstall the previous bundle first, then the previous collector
if needed. The previous collector still reads and keeps Codex's
`last_success_at` with the same meaning; it stops refreshing it, so the field
disappears after Codex's next successful read. No timestamp changes meaning in
either direction. A new bundle that meets an old collector falls back to `at`
for each row. Offline aging and reset handling still work, but rows retained
after a Claude failure look fresh and a missing provider is not listed.

The five-line contract changed no wire field and no version. Its collector
only chooses and orders rows. Collectors since the [window validation change]
already send version 1 payloads that pass the new phone's checks: bounded
labels, Fable as the only scope, and at most four lines with a provider
missing. Old bundles keep slicing to five and pairing Claude and Fable by
identity alone. Collector and bundle can therefore be deployed and rolled back
independently, in either order.

## Deployment boundary

The documented deployment uses `gogo`, `pebble-quota.service`, and the private
Tailscale endpoint `https://gogo.crane-boa.ts.net:8450/v1/watch`. This repository
contains no service unit or proxy/ACL configuration, so these are deployment
assumptions, not a live-status check. The collector itself serves plain HTTP;
TLS and private network access belong to the deployment. Credentials and tokens
must be provisioned outside the repository for the service user.

The remaining host setup, token rotation/recovery, tested CLI version and release
recovery runbook are tracked by the [operations proposal]. This source review
does not establish current production configuration or authorize a restart.

[collector]: ../collector/pebble_quota.py
[five gauge lines]: #five-gauge-lines
[wire identity]: #wire-identity
[window validation change]: tasks/8-validate-windows-and-loaded-snapshots-before-publication.md
[quick start]: ../README.md#collector
[phone settings]: ../watchface/README.md#phone-settings
[Codex adapter task]: tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md
[state timestamp semantics]: https://contributors.home-assistant.io/core/internals/states/
[watchface guide]: ../watchface/README.md
[operations proposal]: tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[phone response ordering]: ../watchface/README.md#phone-settings
[documentation recheck]: reviews/2026-10-25-docs-recheck.md

[kandev-pacer]: http://hopeli/prg/kandev-pacer/?f
