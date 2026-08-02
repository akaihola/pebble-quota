# 001: Quota collectors

**Question:** Can `gogo` obtain live five-hour and weekly usage percentages and reset times for Claude Code and Codex without screen scraping or exposing credentials?

## Given / When / Then

Given the existing authenticated Claude Code and Codex installations, when this probe runs, then it should emit normalized JSON containing `used_fraction`, `resets_at`, and `duration_seconds` for each available quota window.

## Approaches

- **Claude Code:** call the OAuth usage endpoint used by Claude Code itself. This endpoint is undocumented and therefore guarded by explicit error output.
- **Codex:** use the supported local `codex app-server` JSON-RPC method `account/rateLimits/read`.

## Run

```bash
python3 spikes/001-quota-collectors/probe.py
```

No credential value is printed or written.

## Verdict: VALIDATED

### What worked

- Claude returned live `5h` and `7d` windows through its OAuth usage endpoint.
- Codex returned live quota data through `account/rateLimits/read`.
- No credentials were printed or persisted.

### Surprise

Codex `primary` and `secondary` are not stable names for five-hour and weekly windows. On this account, only a 10,080-minute window was present. The collector must label windows using `windowDurationMins`.

### Recommendation for the real build

Promote these collectors into a small standard-library Python service, preserve missing windows rather than inventing them, and expose a compact authenticated JSON endpoint for PebbleKit JS.
