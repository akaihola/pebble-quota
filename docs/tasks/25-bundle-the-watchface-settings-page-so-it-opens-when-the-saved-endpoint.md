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
