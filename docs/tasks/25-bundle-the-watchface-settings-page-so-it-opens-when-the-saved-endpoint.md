# Bundle the watchface settings page so it opens when the saved endpoint is down

Reported by Antti, 2026-10-23: the watchface's Settings page in the Pebble
phone app is blank, so the collector URL cannot be changed. The collector moved
from hopeli to tinni on 2026-10-23 and the watch still points at hopeli.

## Cause

The phone script opens `<saved endpoint origin>/config`, a page the collector
serves itself. With the saved host gone, the webview has nothing to load. The
built-in default (gogo) is off too, so reinstalling does not help either.

## Work

- Ship the settings page in the phone script and open it as a
  `data:text/html` URL, as Clay does. The Core Devices app loads such URLs and
  intercepts `pebblejs://close#`.
- Accept the collector URL (`https://host:port`) or the older full `/v1/watch`
  endpoint; the phone appends `/v1/watch`.
- Leave the saved token unchanged when the field is blank, and stop putting the
  saved token in the settings URL.
- Default the collector to tinni.
- Keep the collector's `/config` route for faces still on 0.2.0.
- Bump the watchface to 0.3.0, with a `Release-As: 0.3.0` footer because the
  Release Please manifest still says 0.1.0.

## Acceptance

- In a headless browser, the generated settings URL shows Collector URL and
  Token fields with the saved collector URL filled in, and Save navigates to
  `pebblejs://close#…`.
- In a Node VM with mocked Pebble, localStorage and XHR, feeding that close
  payload to `webviewclosed` stores the URL, the next request goes to
  `<url>/v1/watch` with the saved bearer token, and the response reaches
  `Pebble.sendAppMessage`. A saved full `/v1/watch` endpoint still works.
- `make clean build` produces a PBW whose appinfo carries version 0.3.0.
- Installing on the watch and checking it there is Antti's step.

## Outcome and verification

Fixed in `4768514` on branch `fix-empty-settings-page`, rebased on 2026-10-27
onto `main` at `0a8e369`, which had reworked the phone script's validation and
ordering. The fix keeps that logic and only changes how the URL is built.

Cause confirmed on 2026-10-23: the collector on tinni answers `/config` (200)
and `/v1/watch` (401 without a token) through its tailnet URL, while the same
port on hopeli refuses connections. The Core Devices app's settings screen
loads `data:text/html;charset=utf-8,` URLs and intercepts
`pebblejs://close`, decoding the payload before `webviewclosed`; the phone
script's second decode is harmless for this JSON.

- `PhoneSettingsTests` in [the test suite](../../tests/test_pebble_quota.py)
  drive the phone script through [the phone harness](../../tests/watch/phone.js),
  which now seeds saved settings, records `openURL` and can pass the close
  payload already decoded. All three fail on `main`'s phone script. The full
  suite (111 tests) passes. Ruff and ty report seven findings, all in files
  this change leaves alone (`collector/pebble_quota.py` and `spikes/`).
- Headless Chromium, rerun after the rebase, rendered the generated settings URL for a saved
  `https://hopeli.crane-boa.ts.net:8450/v1/watch`: labels `Collector URL` and
  `Token`, the URL field filled in as `https://hopeli.crane-boa.ts.net:8450`,
  the token field empty. Entering ` https://tinni.crane-boa.ts.net:8450 ` and
  pressing Save navigated to `pebblejs://close#` with
  `{"endpoint":"https://tinni.crane-boa.ts.net:8450","token":""}`.
- That close URL, fed to `webviewclosed` in a Node VM whose XHR forwarded to
  the real collector `Handler` on loopback (synthetic snapshot and token),
  saved the URL and kept the token (rerun after the rebase). It requested
  `https://tinni.crane-boa.ts.net:8450/v1/watch` with `Authorization`, and
  passed `COLLECTED_AT`, `ROW_COUNT` 1 and the row to `Pebble.sendAppMessage`.
- After the rebase, `make clean build` with Pebble tool 5.0.40 and SDK 4.17
  (CI pins 4.33.1) built a PBW with `versionLabel` 0.3.0, the same UUID, `emery` and
  `configurable`; `unzip -t` reports no errors. SHA-256
  `b4778aa6453193f07a8aa4e64f6afe7db925106cb15f8d3f063b4cd79eaf0219`.

Not verified: installing on the watch, opening Settings in the phone app, and
quota reaching the watch from tinni with the real token. The collector's
`/config` route stays for faces still on 0.2.0.
