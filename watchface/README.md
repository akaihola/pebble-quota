# Quota Pace watch face

Pebble Time 2 (`emery`) watch face for Claude Code and Codex subscription quotas.

The layout stacks three regions top to bottom:

1. **Time:** a large black-on-white band. When the phone provides a fresh
   temperature, it appears on the right in whole Celsius degrees, rounded to
   nearest with ties away from zero (for example, `22°`).
2. **Calendar:** a colored three-week calendar, Monday-first. Today sits in the
   middle week inside a white box; other weekends are red and adjacent-month
   days are dimmed.
3. **Pace bars:** gauges for the received quota windows, typically `Claude 5h`,
   `Claude+Fable 7d`, `Codex 5h` and `Codex 7d`. Missing windows are not invented.

Each gauge shows the service/window title, used quota over a light-gray remaining
track, and a white, black-outlined elapsed-time marker. With no rows the face
shows `Waiting for quota data`. The watch re-judges every row each minute
against its own clock:

- **Fresh:** the color comes from the current elapsed percentage minus the used
  percentage, the same elapsed value that places the marker. Green means pace
  surplus is zero or positive, yellow means -10 through -1 points, and red means
  below -10.
- **Stale:** the reading is more than 25 minutes old, its provider's latest
  attempt failed, or it is more than 5 minutes in the future. The used part
  turns dark gray, and the title row shows `stale 12m` (or hours, then days) or
  `clock skew`.
- **Reset:** the window has reset since the reading. The bar becomes an empty
  dark track without a marker, and the title row shows `reset ?`.
- **Unavailable:** a provider without rows gets its own line, for example
  `Codex` with `unavailable`, over an empty dark track.

The first title row shows `updated Nm ago` or `phone sync pending` while that
gauge is fresh, and the gauge's own state otherwise. The temperature hides once
its pass is more than 25 minutes old. Only a newer valid reading clears a stale
state.

When both Claude and Fable weekly rows exist, they share two bars separated by
1 px and a single marker computed from Claude's row. Pairing assumes equal
resets and durations but does not check them. Both bar colors use that shared
elapsed value. See [collector freshness] for the policy, timestamp meaning,
temperature validation, and rollout order.

The rules live in [the gauge module], which has no Pebble dependency; the test
suite compiles it on the host.

![Pebble Time 2 emulator screenshot][screenshot]

## Calendar date math

The grid uses `(tm_wday + 6) % 7` to put today in the middle week. The renderer
anchors at local noon with `mktime`, adds multiples of 86,400 seconds, then uses
`localtime` for each cell. Noon avoids ordinary overnight DST transitions; this
is not a guarantee for every timezone transition.

A previous manual host-harness check covered month/year boundaries, leap day
2028-02-29 and an EU DST-change Sunday. The harness is not tracked, so this is
historical evidence, not a reproducible check in the current test suite.

## Build

From the repository root:

```bash
cd watchface
make clean build
```

The [watchface build recipe] selects the ARM compiler from the locally active Pebble SDK
(`SDKs/current`), with `PEBBLE_CC` available as an override. It passes only
`HOME`, `PATH`, `LANG` and `CC` to the build/clean commands. Calling `pebble build`
directly on the documented NixOS host may instead select its host compiler
wrapper.

The [CI workflow] pins Python 3.12.3, Node 24, Pebble tool 5.0.40 and SDK 4.33.1;
the recipe itself does not pin an SDK version. A local build needs the Pebble
CLI on `PATH` and an installed active SDK/toolchain. Output is the
[installable bundle].

## Emulator screenshot

The recorded headless `gogo` workflow uses an X display and the library closure
in [the Nix shell]. Run from the watchface directory after building:

```bash
nix-shell --run 'xvfb-run -a sh -c "pebble install --emulator emery && sleep 3 && pebble screenshot --emulator emery quota-pace.png && pebble kill"'
```

This path and the checked-in screenshot are historical evidence; the 2026-10-22
source review did not run an emulator or device. On 2026-10-24 the
[freshness change] was checked this way against synthetic loopback snapshots;
its task record describes each capture.

## Install on a physical Pebble

Copy the [installable bundle] to the phone (USB, Syncthing, or a download), then
open it with the Pebble app to sideload over the installed face. Alternatively,
enable the developer connection in the phone app and run this from the watchface
directory:

```bash
pebble install --phone <phone-ip>
```

Open the installed face's **Settings** (gear icon) and configure it as below.

## Phone settings

The [phone script] defaults to:

```text
Endpoint: https://gogo.crane-boa.ts.net:8450/v1/watch
Token:    test-only-token
```

A phone needs access to that tailnet endpoint and the real service token. Saved
phone localStorage values override both defaults. Saving nonempty endpoint/token
values triggers an immediate refresh; a blank field keeps its old value.
Persistence across reinstalls is not established by localStorage use alone.

Settings are hosted by the collector: the phone removes a trailing `/v1/watch`
(with an optional final slash) from the saved endpoint and appends `/config`.
For the default endpoint, this is:

```text
https://gogo.crane-boa.ts.net:8450/config
```

The page requires no bearer authentication. The current phone script adds the
endpoint and existing service token in URL query parameters for prefill; quota
fetches use `Authorization: Bearer`. Provider credentials remain on the collector
host. Token-free configuration transport and an independent recovery page remain
in the [settings recovery proposal]. An invalid saved endpoint or collector
outage can prevent Settings from opening; it is not always reachable.

The phone refreshes when ready, every 15 minutes, on a watch sync request, and
after saving settings. HTTP requests time out after 15 seconds. Failures are
logged; there is no immediate retry or ordering guard for overlapping responses.
The watch requests a sync at startup and holds rows in memory only, so restarting
the face offline starts without quota data. The [request ordering proposal]
covers delayed responses overwriting newer settings or data.

## Releases

Release Please is configured to bump the watchface to the next `major.minor.0`
version in [the package manifest]. Merge its release PR to release: the
[CI workflow] builds the bundle, checks archive/identity/version metadata, then
runs Release Please and uploads the matching artifact when a release is created.
Tags use `vX.Y.0`; assets use `pebble-quota-emery-X.Y.0.pbw`.

The workflow uses `RELEASE_PLEASE_TOKEN` when configured, otherwise `github.token`.
The documented setup uses a fine-grained personal access token with Contents,
Issues and Pull requests read/write access so generated release PRs receive CI.
Actual repository token permissions and live release state were not inspected.
The [release configuration] and [release manifest] are the source of versioning
settings; their reconciliation and upload-retry procedure remain in the
[operations proposal]. Collector deployment is outside this workflow.

[collector freshness]: ../docs/collector.md#display-freshness-policy
[the gauge module]: src/c/gauges.c
[freshness change]: ../docs/tasks/9-carry-freshness-and-failure-status-through-to-watch-rendering.md
[screenshot]: quota-pace.png
[watchface build recipe]: Makefile
[CI workflow]: ../.github/workflows/build.yml
[installable bundle]: build/watchface.pbw
[the Nix shell]: shell.nix
[phone script]: src/pkjs/index.js
[settings recovery proposal]: ../docs/tasks/6-remove-token-url-transport-and-make-settings-recoverable.md
[request ordering proposal]: ../docs/tasks/14-prevent-older-phone-responses-from-overwriting-newer-settings-or-data.md
[the package manifest]: package.json
[release configuration]: ../release-please-config.json
[release manifest]: ../.release-please-manifest.json
[operations proposal]: ../docs/tasks/12-document-recoverable-operation-and-reconcile-build-release-assumptions.md
