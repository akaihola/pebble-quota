# Security review of pebble-quota, 2026-10-21

Review for [the security-scan task][task-15], on `main` at `d13f4d2`. It covers
[collector/], [watchface/], [spikes/], [tests/] and [the build workflow][workflow],
plus the deployment pieces in nixos-config and kandev-pacer that decide how the
collector actually runs. Nothing was fixed. No credential file was opened, no
provider was called, nothing was pushed and no service was restarted.

Secret values appear nowhere in this report. Credential and secret-bearing files
are named in code spans and deliberately not linked: a link would put their
contents one click away in Filemill.

## Urgent: secrets readable outside the agent account

Two ignored build files in the shared checkout hold a plaintext snapshot of
agent's environment, including Home Assistant's long-lived token and five paid
API keys. They are readable by the `coleaders` account, which runs the
Slack-connected Hermes gateway. Details and the drafted fix are in [F1][f1].

- `agent@hopeli:~/prg/pebble-quota/watchface/.lock-waf_linux_build`
- `agent@hopeli:~/prg/pebble-quota/watchface/build/.lock-waf_linux_build`

An older snapshot of the same kind is in local-only history: commit `fb44f85`,
file `watchface/.lock-waf_linux_build`. It was never pushed (see [History
scan][history]). No credential is in any tracked file or in any commit
GitHub has.

## Scope and method

- **Static review:** every line of the collector, phone script, watch C code,
  spike, tests and workflow, against the questions in the task.
- **Deployment facts:** the user unit, Tailscale Serve mapping and secrets layout
  in nixos-config; live unit properties from `systemctl --user show` (read-only);
  the modes of the state directory, snapshot, env file and checkout. File
  contents were read only for `latest.json` (structure, with long strings masked)
  and for the waf lock files' variable names.
- **Behaviour checks, all with mocks:** the test suite under an empty fake `HOME`
  with no `codex` on `PATH` (38 passed); a probe of `serve` startup with mocked
  collectors; urllib's and http.server's source for redirects and status lines.
- **History:** a scan of every object in the shared `.git` (see [History
  scan][history]), plus three unauthenticated GitHub API requests: repository
  visibility and the two initial commits.

## Findings ranked by impact and likelihood

- **F1, high:** build-environment snapshots with live secrets are readable by
  other local accounts and by Filemill.
- **F2, medium:** any startup failure becomes a provider-polling loop every few
  seconds, without backoff when the snapshot can't be written.
- **F3, medium:** the Claude cooldown protects only the `serve` process. Manual
  `collect` runs and kandev-pacer's live reads of the same endpoint with the same
  token ignore it.
- **F4, low–medium:** the Claude OAuth token and the HA token follow HTTP
  redirects to any host, including HTTPS-to-HTTP.
- **F5, low–medium:** the release path runs third-party actions pinned by mutable
  tags with write permissions and a personal access token.
- **F6, low–medium:** the service token travels in the settings URL, and the
  phone's default endpoint still names gogo after the move to hopeli. The first
  part is already tracked as [removing token URL transport][task-6].
- **F7, low:** the Codex subprocess inherits every secret in the service
  environment.
- **F8, low:** nothing stops a future test from reaching real credentials on
  hopeli.
- **F9, low:** snapshot privacy depends on the unit's `UMask`; manual runs write
  world-readable files through a fixed temporary name.
- **F10, low:** a 503 response copies raw exception text into the HTTP status
  line.

## Finding details

### F1. Build-environment snapshots expose secrets

The Pebble SDK's waf records the whole process environment in
`.lock-waf_<platform>_build` when `pebble build` configures. agent's environment
carries every `environment.d` secret, so each build in [watchface/] writes those
secrets to disk in plaintext with the default mode 0644.

- **Evidence, working tree:** the two files listed under [Urgent][urgent],
  written 2026-09-04, mode 0644, ignored by [.gitignore:6–7][gitignore] and
  untracked. Their `environ` entry holds values for `HASS_TOKEN`,
  `GEMINI_API_KEY`, `KAGI_API_KEY`, `PERPLEXITY_API_KEY`, `BRAVE_API_KEY`,
  `ELSEVIER_API_KEY`, `KANDEV_DESKTOP_HEALTH_TOKEN` and
  `KANDEV_GITHUB_CREDENTIAL_LEASE`. Only names were read.
- **Evidence, history:** commit `fb44f85`, local-only; see [History
  scan][history].
- **Who can read them:** `/home/agent` is mode 0710 with group `users`;
  `~/prg`, the checkout and `watchface/` are 0755. `akaihola` and `coleaders`
  both have primary group `users`. `coleaders` is a normal account
  ([agent@hopeli:~/repos/nixos-config/nixos/features/coleaders.nix:29–31][coleaders])
  that runs the Slack-connected Hermes gateway. Its unit
  ([agent@hopeli:~/repos/nixos-config/home-manager/home-coleaders.nix:200][coleaders-hm])
  sets no filesystem sandboxing; whether Hermes runs its tools in a container
  was not checked. Filemill serves agent's whole home over Tailscale
  Serve ([agent@hopeli:~/repos/nixos-config/home-manager/features/agent-workloads.nix:253][hm-workloads]).
  Whether Filemill filters these files was not tested, because testing would
  fetch them.
- **Impact:** high. `HASS_TOKEN` is a long-lived token for gogo's Home Assistant,
  which controls the home. The rest are paid API keys and kandev tokens.
- **Likelihood:** medium. The exposure exists now. Exploiting it needs a process
  under another account, or a Filemill client, to look there, and the
  `coleaders` agent takes its instructions from Slack.
- **Liveness:** not tested, since testing means using them. Treat them as live.

Drafted issue:

- **Title:** Remove waf environment snapshots and rotate the secrets they hold
- **Work:**
  1. Operator: delete both lock files in the shared checkout, and in any gogo
     checkout where the face was built. Rotate `HASS_TOKEN` first, then the
     Gemini, Kagi, Perplexity, Brave and Elsevier keys and
     `KANDEV_DESKTOP_HEALTH_TOKEN`; confirm the kandev GitHub credential lease
     has expired.
  2. Make [watchface/Makefile][makefile] run `pebble build` and `pebble clean`
     under `env -i`, passing only `HOME`, `PATH`, `LANG` and whatever else the
     SDK needs, so a regenerated lock file cannot capture secrets.
  3. Drop the `main` and `HEAD` reflog entries for `fb44f85` and prune
     unreachable objects, at a time when no other session uses the shared
     `.git` (T3 Code and kandev keep refs there).
  4. File in nixos-config's tracker: whether `/home/agent` needs group traverse
     for `users`, whether agent sessions should run with umask 077, and what
     Filemill should serve.
- **Acceptance:**
  - After `make clean build`, no `.lock-waf_*` file under the checkout has an
    `environ` entry whose name matches `TOKEN|SECRET|KEY|PASS`, checked by name
    only.
  - `git cat-file -e fb44f85` and `git cat-file -e b8f1113` fail in the shared
    repository.
  - A rotation record names each rotated key and its date, without values.
    An operator confirms `coleaders` cannot read agent's checkouts.

### F2. Startup failures become a provider-polling loop

`serve` collects from both providers before it binds its port, and any
exception other than the "all collectors failed" `RuntimeError` ends the
process. The unit restarts it 5 s later, and systemd's start limit cannot trip
at that pace.

- **Evidence, code:** [collector/pebble_quota.py:467–480][collector] runs
  `refresh_snapshot()` before `QuotaServer(...)` binds, and catches only
  `RuntimeError`. [collector/pebble_quota.py:337–341][collector] lets `OSError`
  from writing the snapshot propagate. A probe with mocked collectors confirmed
  both paths: with the port in use, and with an unwritable state directory,
  `main()` exits after one Claude and one Codex call.
- **Evidence, unit:**
  [agent@hopeli:~/repos/nixos-config/home-manager/features/agent-workloads.nix:219–221][hm-workloads]
  sets `Restart=on-failure` and `RestartSec=5`. `systemctl --user show` reports
  `StartLimitBurst=5` per `StartLimitIntervalSec=10s`. A 5 s restart delay allows
  at most two starts per window, so the limit never stops the loop. `NRestarts=0`
  since 2026-10-18, so this has not happened yet.
- **Triggers:** port 8765 already taken, for example by a manual `serve`; a full
  disk on this small shared host; an unwritable state directory; a first start
  with no snapshot while both providers fail, for example on an expired Claude
  token.
- **Impact:** medium. A Claude request and a fresh Codex app-server every 6–20 s
  is the pattern most likely to get either subscription rate-limited or flagged.
  If the snapshot can't be written, the persisted 429 cooldown can't take effect
  either, so Claude gets no backoff. Codex never has one.
- **Likelihood:** medium–low. It needs one of the triggers above.

Drafted issue:

- **Title:** Bind before collecting and keep startup failures from re-polling providers
- **Work:**
  1. In `main()`, bind the server before any collection, and run the first
     refresh in the refresher thread.
  2. Treat every exception from `refresh_snapshot()`, including write errors,
     as non-fatal. Log its type and message and keep serving.
  3. Keep the last collection in memory as `previous`, so the Claude cooldown
     holds even when the file can't be written.
  4. Persist a per-provider `last_attempt_at`. On start, skip any provider
     attempted less than `--refresh-seconds` ago, so restarts cannot increase
     request rates.
  5. In nixos-config, give the unit a start limit that can trip at this restart
     delay, for example `StartLimitIntervalSec=600`, or a growing restart delay.
- **Acceptance:**
  - With the port in use, `serve` exits without calling either collector.
  - With an unwritable state directory, the process keeps running, a 429
    cooldown is honoured from memory, and the next refresh within the interval
    makes no Claude request.
  - Two process starts within `--refresh-seconds` contact each provider once.
  - Existing tests pass.

### F3. The Claude cooldown protects only one client

The 429 handling from [backing off on HTTP 429][task-2] works for the `serve`
process: it persists `retry_at`, honours `Retry-After` seconds and dates, and
backs off 10, 20, 40 and then 60 minutes. Two other paths ignore it.

- **Evidence, manual runs:** `collect` defaults to `latest.json` in the working
  directory ([collector/pebble_quota.py:452][collector]), and [README.md:9–12][readme]
  documents it without `--output`. The unit writes
  `~/.local/state/pebble-quota/latest.json`, so a manual `collect` never sees
  the production `retry_at`. A stale snapshot from such a run dated 2026-08-02
  sits in the shared checkout
  ([agent@hopeli:~/prg/pebble-quota/latest.json][stale-snapshot]).
- **Evidence, kandev-pacer:** with `quota_source = "pebble"` it still makes its
  own live Claude reads to supplement the snapshot
  ([agent@hopeli:~/prg/kandev-pacer/src/kandev_pacer/provider.py:657–681][pacer-provider]).
  They use the same endpoint and OAuth token, cache failures for 15 s
  ([agent@hopeli:~/prg/kandev-pacer/src/kandev_pacer/provider.py:53–54 and 596–610][pacer-provider]) and ignore `Retry-After`,
  as the 429 task found. With the pacer's 30 s loop
  ([agent@hopeli:~/repos/nixos-config/home-manager/features/agent-workloads.nix:191][hm-workloads]), a rate-limited token can be retried
  about every 30 s while pebble-quota waits. The full loop path was not traced.
- **Impact:** medium. The cooldown limits pebble-quota's own share of requests,
  but not the account's.
- **Likelihood:** medium. The pacer runs continuously, and agents run `collect`
  when debugging.

Drafted issue for this repository:

- **Title:** Make manual `collect` honour the production cooldown
- **Work:**
  1. Default `--output` to `~/.local/state/pebble-quota/latest.json`, or to a
     `PEBBLE_QUOTA_OUTPUT` variable the unit also sets, and update
     [README.md][readme].
  2. Remove the stale snapshot from the shared checkout (operator).
- **Acceptance:**
  - With a future Claude `retry_at` in the snapshot at the default path,
    `collect` makes no Claude request.
  - The README's commands use the same state as the service.

Drafted issue for kandev-pacer's tracker:

- **Title:** Honour pebble-quota's Claude cooldown and back off on 429
- **Work:** when the Pebble snapshot's `services.claude.retry_at` lies in the
  future, skip the live Claude read. After a 429 from the usage endpoint, wait
  for `Retry-After`, or back off exponentially, instead of the 15 s failure TTL.
- **Acceptance:** tests show no live read during a Pebble cooldown, and no
  second read after a 429 before the backoff ends.

### F4. Bearer tokens follow redirects

`urllib.request` copies every header except content headers onto the redirected
request, whatever the target host or scheme. This was confirmed in the installed
Python 3.14's `HTTPRedirectHandler.redirect_request`.

- **Evidence:** the Claude request ([collector/pebble_quota.py:114–122][collector])
  and the HA request ([collector/pebble_quota.py:210–214][collector]) pass
  `Authorization` through `headers=`, which redirects copy. The spike does the
  same ([spikes/001-quota-collectors/probe.py:39–47][probe]).
- **Related:** the service-token check compares strings with `!=`
  ([collector/pebble_quota.py:426–427][collector]). It is not constant-time,
  though timing it through Tailscale Serve is impractical.
- **Impact:** high if it happens. The Claude OAuth access token gives use of the
  whole subscription.
- **Likelihood:** very low. It needs `api.anthropic.com`, or the HA instance
  behind `HASS_SERVER`, to answer with a redirect to a host the attacker
  controls.

Drafted issue:

- **Title:** Keep bearer tokens off redirects and compare the service token in constant time
- **Work:**
  1. Send `Authorization` with `Request.add_unredirected_header()`, or use an
     opener that refuses redirects, for both the Claude and HA requests. Record
     a 3xx as an error.
  2. Move the Claude URL into a module constant so tests can point it at a
     local server.
  3. Compare the `Authorization` header with `hmac.compare_digest`.
  4. Mark the spike historical, as [documenting recoverable operation][task-12]
     proposes, or apply the same change there.
- **Acceptance:**
  - A local server answering 302 to a second local server: the second server
    receives no `Authorization` header, for both collectors.
  - Existing authentication tests pass unchanged.

### F5. Release actions are pinned by mutable tags

The workflow's defaults are sound: [.github/workflows/build.yml:9–10][workflow] sets read-only
`contents`, pull requests use `pull_request` rather than `pull_request_target`,
and release outputs reach the shell through `env:` rather than inline
expressions ([.github/workflows/build.yml:105–118][workflow]). The release jobs still trust tags.

- **Evidence:** `googleapis/release-please-action@v4` follows a moving major tag
  ([.github/workflows/build.yml:86–89][workflow]) and runs with `contents`, `issues` and
  `pull-requests` write ([.github/workflows/build.yml:77–80][workflow]) and the
  `RELEASE_PLEASE_TOKEN` personal access token. Every other action is pinned by
  version tag, and `pebble-tool` comes from PyPI by version, without a hash
  ([.github/workflows/build.yml:35][workflow]).
- **Impact:** medium. A moved tag could rewrite releases or the `.pbw` that
  phones sideload, and the phone script holds the service token. It could also
  take the PAT.
- **Likelihood:** low.

Drafted issue:

- **Title:** Pin release-path actions to commit SHAs
- **Work:** pin every `uses:` to a full commit SHA with a version comment. Add a
  Dependabot entry for `github-actions`. Confirm the PAT is limited to this
  repository with the three documented permissions. Set
  `persist-credentials: false` on the checkouts that don't push.
- **Acceptance:** every `uses:` line names a 40-character SHA; the Dependabot
  configuration exists; the PAT's scope is recorded without its value.

### F6. The settings URL carries the token

The phone puts the stored service token into the `/config` query string, and
derives that page's host from the saved endpoint
([watchface/src/pkjs/index.js:58–67][phone-js]). The settings page accepts any
endpoint and scheme ([watchface/src/pkjs/index.js:69–79][phone-js]). This is the architecture
review's F4, tracked as [removing token URL transport][task-6].

New since that review: the collector moved to hopeli on 2026-10-18
([agent@hopeli:~/repos/nixos-config/nixos/configuration-gogo.nix:57][gogo-config]),
but the phone's default endpoint ([watchface/src/pkjs/index.js:3][phone-js]), [README.md:120–124][readme]
and [watchface/README.md:73–80][watch-readme] still name
`gogo.crane-boa.ts.net:8450`. A phone that saved the old default sends its
token, in both the header and the settings URL, to whatever answers on gogo's
port 8450.

- **Impact:** low–medium. The service token only reads quota data.
- **Likelihood:** medium for the URL, low for the stale host.

**Recommendation:** extend the token-URL task rather than file a new issue. Add
to its work: point the default endpoint and both READMEs at hopeli, or drop the
hardcoded default, and check the physical phone's saved endpoint.

### F7. Codex inherits every service secret

`collect_codex()` starts `codex app-server` with the full service environment
([collector/pebble_quota.py:141–149][collector]). On hopeli that includes
`PEBBLE_QUOTA_TOKEN` from the unit's environment file, `HASS_TOKEN`, and every
API key from `environment.d`, which reaches all user services
([agent@hopeli:~/repos/nixos-config/home-manager/features/agent-workloads.nix:199–227][hm-workloads]).

- **Impact:** low. Codex runs as the same user and could read those files
  anyway. Scrubbing the environment only removes accidental capture, the way
  waf captured it in F1.
- **Likelihood:** low.

Drafted issue:

- **Title:** Start the Codex app-server with a minimal environment
- **Work:** pass only `HOME`, `PATH`, `TERM`, locale variables, `CODEX_HOME` and
  proxy variables when set. This fits the fake app-server tests that
  [reporting Codex RPC failures][task-10] already requires.
- **Acceptance:** a fake `codex` on `PATH` records the names in its environment.
  `PEBBLE_QUOTA_TOKEN`, `HASS_TOKEN` and `*_API_KEY` are absent, and collection
  still succeeds.

### F8. Tests have no guard against live calls

Every current test patches its network and subprocess access: synthetic
credentials under a patched home, mocked `urlopen` and `collect_codex`, and
servers on `127.0.0.1:0` ([tests/test_pebble_quota.py:123–142][tests]). The
suite passed with an empty fake `HOME` and no `codex` on `PATH`. Nothing fails
closed, though: a future test that forgets one patch would use agent's real
Claude token on hopeli, where the suite runs.

- **Impact:** medium. It would make a real provider call with real credentials.
- **Likelihood:** low.

**Recommendation:** add this to [gating releases on behaviour checks][task-7]
rather than file a new issue. A `setUpModule` guard should make `urlopen`,
`subprocess.Popen` and reads of `~/.claude` raise unless a test overrides them.

### F9. Snapshot privacy depends on the unit's umask

`write_snapshot()` writes with the default mode through a fixed `latest.json.tmp`
name ([collector/pebble_quota.py:337–341][collector]). Production is private only
because the unit sets `UMask=0077`: the state directory is 0700 and the snapshot
0600. A manual run writes 0644, like the stale snapshot in F3. The snapshot holds
no token, so the exposure is quota levels and error text.

- **Impact:** low.
- **Likelihood:** low.

**Recommendation:** fold this into the F3 issue for this repository. Create the
temporary file with `tempfile.mkstemp` in the target directory, which gives mode
0600 and a unique name, then `os.replace` it. Test the mode under umask 022.

### F10. 503 responses reflect exception text

The handler passes `str(exc)` to `send_error(503, ...)`
([collector/pebble_quota.py:430–435][collector]). `http.server` HTML-escapes it
in the body but writes it raw into the status line. Exceptions from a malformed
snapshot can carry provider-supplied field values: `fromisoformat` quotes the
bad string. CR/LF in such a value could therefore inject response headers, and
non-Latin-1 text makes the handler fail mid-response. Only authenticated clients
see these responses, and the data comes from Anthropic, OpenAI or the local file.

- **Impact:** low.
- **Likelihood:** very low.

**Recommendation:** no new issue. [Validating windows and loaded
snapshots][task-8] already requires sanitized diagnostics instead of raw
exception text. Add a test there for a CR/LF value in a window field.

## Coverage of the requested areas

- **Finding, refreshing and holding provider tokens:**
  - **Claude:** each refresh reads `claudeAiOauth.accessToken` from
    `~/.claude/.credentials.json` ([collector/pebble_quota.py:109–113][collector])
    and keeps it in a local variable for one request. It never writes, caches
    or refreshes the token; Claude Code owns refresh, and kandev-pacer documents
    the same rule. An expired token produces a recorded 401 every refresh until
    Claude Code refreshes it.
  - **Codex:** the collector never sees Codex tokens. The app-server reads and
    refreshes its own auth, and a new one starts every 5 minutes. nixos-config
    notes that the agent's services share rotating Codex refresh tokens
    ([agent@hopeli:~/repos/nixos-config/docs/contributing/hopeli-agent-services.md][hopeli-services]). Whether an app-server
    refreshes on start was not verified.
  - **HA:** `HASS_TOKEN` comes from `environment.d`; `HASS_SERVER` comes from the
    unit.
  - **Service token:** `PEBBLE_QUOTA_TOKEN` comes from a 0600 environment file
    in a 0700 directory and is required to be non-empty
    ([collector/pebble_quota.py:461–463][collector]).
- **Whether a token, header or raw response can leak:**
  - **`latest.json`:** it gets normalized fields and per-service
    `"Type: message"` errors ([collector/pebble_quota.py:277–300][collector]).
    `HTTPError` text carries only the status code and reason, and JSON decode
    errors carry positions, not content. A provider value can appear inside a
    `ValueError` message, but no token or raw response body can. The production
    snapshot's structure confirmed this: normalized windows and one
    `URLError: <urlopen error timed out>` from HA.
  - **Logs:** only refresh failures are printed
    ([collector/pebble_quota.py:364–369][collector]), as fixed messages or
    filesystem errors. Request logging is suppressed
    ([collector/pebble_quota.py:443–444][collector]).
  - **Caches and error messages:** there is no cache besides the snapshot, and
    the phone's localStorage holds the service token by design. The 503 status
    line is covered by F10, the settings URL by F6, and the build snapshots by F1.
- **Permissions of what it writes:** production is private through the unit's
  `UMask` only (F9); the lock files are 0644 (F1).
- **Hosts and whether any comes from input:** `api.anthropic.com` is hardcoded.
  The HA host comes from the unit's environment (production:
  `http://gogo.crane-boa.ts.net:8123`, plain HTTP inside the tailnet,
  [agent@hopeli:~/repos/nixos-config/nixos/configuration-hopeli.nix:51][hopeli-config]). Codex contacts its own hosts.
  No collector host comes from a request or from the snapshot, but redirects can
  move a token (F4). On the phone the endpoint comes from user input on the
  settings page (F6).
- **What the watch face side exposes, and to whom:**
  - **API:** `/v1/watch` serves quota rows and temperature to holders of the
    service token, through Tailscale Serve rather than Funnel
    ([agent@hopeli:~/repos/nixos-config/nixos/features/agent-workloads.nix:118–124][nixos-workloads]), so only
    tailnet devices reach it. Tailscale ACLs were not reviewed.
  - **Settings page:** `/config` is static and unauthenticated. Its script
    assigns query values to `.value`, so it cannot inject markup
    ([collector/pebble_quota.py:392–398][collector]).
  - **Phone and watch:** the phone logs status codes only
    ([watchface/src/pkjs/index.js:24–54][phone-js]), and sends the watch no token. The watch bounds
    its string copies and row count
    ([watchface/src/c/watchface.c:313–349][watch-c]); unchecked numeric tuple
    types are covered by [enforcing the five-row contract][task-11]. The face
    shows usage and outside temperature to anyone who sees the watch.
- **Whether HTTP 429 retries could get the account limited or flagged:**
  - **Steady state:** at most one Claude request per 5 minutes plus collection
    time, about 288 a day, under an honest `pebble-quota/0.1` user agent.
  - **After a 429:** the persisted cooldown is conservative and well tested.
    Honouring a large `Retry-After` without a cap is the right choice, since the
    data is then marked stale.
  - **Remaining risk:** it comes from outside that logic, namely the restart
    loop (F2) and clients that don't share the cooldown (F3). The endpoint is
    undocumented and its limit key unknown, as the 429 task recorded.
- **CI:** see F5. Fork pull requests get no secrets, and the cache is keyed by
  versions.
- **Spike:** it shares the collector's token handling and F4. It prints the
  same normalized JSON to stdout and stores nothing.

## History scan

The shared `.git` holds 415 loose objects and no packs. The scan covered all of
them:

- 139 blobs reachable from any ref or reflog, under 52 paths ever tracked
- 13 unreachable blobs
- 92 commit objects, 78 of them reachable, headers and messages included

Trees hold only names and object IDs; the names were listed. `v0.1.0` is a
lightweight tag, so it adds no object.

"Any ref" includes local branches, remote-tracking branches, T3 Code
checkpoint refs and kandev recovery refs. Patterns covered provider and
platform key formats (Anthropic, OpenAI, GitHub, AWS, Slack, Tailscale), JWTs,
private keys, literal bearer tokens, token-like JSON fields, assignments and
dictionary entries whose key names a token, secret, password or API key, and
high-entropy, base64 and hex runs that are not object IDs. Matches were reported
by location, pattern and shape only.

- **One finding:** commit `fb44f85`, file `watchface/.lock-waf_linux_build`,
  blob `b8f1113`. This was the repository's first commit (2026-08-02 09:08:23
  +0300), and its waf environment snapshot holds values for `BRAVE_API_KEY` and
  `ELSEVIER_API_KEY`. Both match their vendors' key formats. It also holds a
  Hermes session routing key, which looks like a chat identifier rather than a
  credential.
- **Reachability:** 20 seconds later the commit was amended into `982d1d2`
  without that file. `fb44f85` survives only in the local `main` and `HEAD`
  reflogs, because `git gc` has never run.
- **Never pushed:** the repository is public, but GitHub's API returns 422 for
  `fb44f85` and 200 for `982d1d2`. `origin/main`'s reflog begins with a push on
  2026-09-04 of history rooted at `982d1d2`.
- **Everything else is benign:** placeholders (`test`, `test-token`,
  `test-secret`, `test-only-token`, `replace-me`), code identifiers, Markdown
  paths, commit and object IDs, T3 Code checkpoint ref names, and GitHub's PGP
  signature on a release-please commit.
- **No provider credential:** no Claude, Codex, OpenAI, Home Assistant, GitHub
  or `PEBBLE_QUOTA_TOKEN` value is in any object.

## Informational notes

- **Public hostnames:** the tailnet name and host names appear in this public
  repository ([watchface/src/pkjs/index.js:3][phone-js], [README.md:120–124][readme]). TLS
  certificate transparency logs disclose them anyway.
- **HA temperature:** the production snapshot currently records an HA timeout;
  this is operational, not a security issue.
- **Spike duplication:** the spike still runs as a second collector; marking it
  historical is part of [documenting recoverable operation][task-12].

## Limits of this review

- No credential, the environment file or the lock files' values were read, and
  no key was tested for liveness.
- Tailscale ACLs, Filemill's filtering, gogo's checkout, the phone app's own
  logs and Tailscale Serve's logging were not inspected.
- No provider was called, so Codex app-server refresh behaviour and the Claude
  endpoint's limits remain as the 429 task left them.
- kandev-pacer was read only where it reads the same Claude endpoint.

[collector/]: ../../collector/
[watchface/]: ../../watchface/
[spikes/]: ../../spikes/
[tests/]: ../../tests/
[collector]: ../../collector/pebble_quota.py
[phone-js]: ../../watchface/src/pkjs/index.js
[watch-c]: ../../watchface/src/c/watchface.c
[makefile]: ../../watchface/Makefile
[probe]: ../../spikes/001-quota-collectors/probe.py
[tests]: ../../tests/test_pebble_quota.py
[workflow]: ../../.github/workflows/build.yml
[gitignore]: ../../.gitignore
[readme]: ../../README.md
[watch-readme]: ../../watchface/README.md
[task-2]: ../tasks/2-back-off-on-http-429-from-claude-s-usage-endpoint-and-keep-the-last-re.md
[task-6]: ../tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[task-7]: ../tasks/7-gate-releases-on-collector-and-phone-behavior-checks.md
[task-8]: ../tasks/8-validate-windows-and-loaded-snapshots-before-publication.md
[task-10]: ../tasks/10-report-codex-rpc-failures-and-reap-the-subprocess-reliably.md
[task-11]: ../tasks/11-enforce-the-five-row-collector-phone-and-watch-contract.md
[task-12]: ../tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
[task-15]: ../tasks/15-security-scan-of-pebble-quota-provider-tokens-outputs-and-history.md
[stale-snapshot]: http://hopeli/prg/pebble-quota/latest.json?f
[hm-workloads]: http://hopeli/repos/nixos-config/home-manager/features/agent-workloads.nix?f
[nixos-workloads]: http://hopeli/repos/nixos-config/nixos/features/agent-workloads.nix?f
[hopeli-config]: http://hopeli/repos/nixos-config/nixos/configuration-hopeli.nix?f
[coleaders]: http://hopeli/repos/nixos-config/nixos/features/coleaders.nix?f
[hopeli-services]: http://hopeli/repos/nixos-config/docs/contributing/hopeli-agent-services.md?f
[gogo-config]: http://hopeli/repos/nixos-config/nixos/configuration-gogo.nix?f
[coleaders-hm]: http://hopeli/repos/nixos-config/home-manager/home-coleaders.nix?f
[f1]: #f1-build-environment-snapshots-expose-secrets
[urgent]: #urgent-secrets-readable-outside-the-agent-account
[history]: #history-scan
[pacer-provider]: http://hopeli/prg/kandev-pacer/src/kandev_pacer/provider.py?f
