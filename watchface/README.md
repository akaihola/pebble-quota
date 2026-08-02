# Quota Pace watch face

Pebble Time 2 (`emery`) watch face for Claude Code and Codex subscription quotas.

Each row shows:

- service and quota window (`C` = Claude Code, `X` = Codex)
- percentage remaining and signed pace surplus
- consumed quota as a colored bar
- ideal constant-use pace as a white marker

Positive pace means quota is ahead of schedule; negative pace means usage is draining too quickly.

## Build on gogo/NixOS

```bash
make clean build
```

The Makefile selects the ARM compiler bundled with Pebble SDK 4.17. Calling `pebble build` directly on this NixOS host may select the host `sccache-cc` wrapper instead.

Output:

```text
build/watchface.pbw
```

## Emulator screenshot

The QEMU emulator needs a temporary X display and a Nix library closure on headless `gogo`:

```bash
nix-shell --run 'xvfb-run -a sh -c "pebble install --emulator emery && sleep 3 && pebble screenshot --emulator emery quota-pace.png && pebble kill"'
```

## Phone-side endpoint

During emulator development, `src/pkjs/index.js` defaults to:

```text
http://127.0.0.1:8765/v1/watch
test-only-token
```

These defaults must be replaced or configured before installing on Android. The collector accepts the token in the `Authorization: Bearer` header; Claude/OpenAI credentials remain on `gogo`.
