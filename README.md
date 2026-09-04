# Pebble Quota

A Pebble Time 2 watch face showing Claude Code and Codex quota consumption against a sustainable, constant-use pace.

## Collector

`gogo` already has authenticated Claude Code and Codex CLIs. The collector keeps those credentials on `gogo`, writes a local snapshot, and serves only compact quota data.

```bash
python3 collector/pebble_quota.py collect
PEBBLE_QUOTA_TOKEN='replace-me' python3 collector/pebble_quota.py serve
```

Authenticated endpoint:

```text
GET /v1/watch
Authorization: Bearer <token>
```

Settings page for the Pebble phone app (no auth — a fresh install has no
token yet):

```text
GET /config
```

Response fields are intentionally compact for PebbleKit JS:

- `s`: `C` for Claude Code, `X` for Codex
- `w`: quota window label
- `u`: integer percentage used
- `r`: reset time as Unix seconds
- `d`: window duration in seconds
- `p`: pace surplus in percentage points; positive is ahead, negative is behind
- `t`: outside temperature in integer tenths of °C (optional; omitted when Home Assistant is unavailable)

Claude collection uses an undocumented OAuth endpoint used by Claude Code itself. Codex collection uses the supported local app-server JSON-RPC method `account/rateLimits/read`.

Outside temperature is a best-effort read of the Home Assistant entity `weather.forecast_koti` (met.no forecast for Koivusyrjä). It uses `HASS_TOKEN` (a Home Assistant long-lived token, kept outside the repo on `gogo`) and `HASS_SERVER` (default `http://localhost:8123`). A Home Assistant outage never blocks quota delivery: the temperature is simply omitted rather than reported as a fabricated value.

## Watch face

The v1 face targets Pebble Time 2 (`emery`). Download the installable `.pbw`
from the [latest GitHub release](https://github.com/akaihola/pebble-quota/releases/latest).

To build it locally:

```bash
cd watchface
make clean build
```

The generated installable bundle is `watchface/build/watchface.pbw`.

![Pebble Time 2 emulator showing live quota pace](watchface/quota-pace.png)

The tested emulator path on headless NixOS is documented in [`watchface/README.md`](watchface/README.md).

### Releasing

Release Please maintains a release PR with the next `major.minor.0` version in
`watchface/package.json`. Merge that PR to release. CI builds the watchface,
creates the matching `vX.Y.0` tag and GitHub release, and uploads the `.pbw`.

Set the `RELEASE_PLEASE_TOKEN` repository secret to a fine-grained personal
access token with Contents, Issues, and Pull requests read/write access so CI
also runs on the generated release PR.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Status

The collector runs continuously on `gogo` as `pebble-quota.service`, refreshing quota data every five minutes. Its loopback API is exposed privately to the tailnet at:

```text
https://gogo.crane-boa.ts.net:8450/v1/watch
```

The authenticated endpoint, PebbleKit JS transport, Emery watch face, and headless-emulator path are working. Physical Android/Pebble deployment still needs a configuration flow that stores this endpoint and the service token in PebbleKit JS local storage without committing the token.
