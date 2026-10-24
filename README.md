# Pebble Quota

A Pebble Time 2 watch face showing Claude Code and Codex quota consumption
against a sustainable, constant-use pace.

## Collector

Run on the host with authenticated Claude Code and Codex CLIs. Provider
credentials stay there; the phone receives compact quota data using a separate
service token.

```bash
python3 collector/pebble_quota.py collect
PEBBLE_QUOTA_TOKEN='replace-me' python3 collector/pebble_quota.py serve
```

`collect` writes a local snapshot and prints the compact payload. `serve`
refreshes in the background and exposes the API on loopback by default.

The watch has room for five gauge lines. A provider without rows takes one for
its `unavailable` line. Rows fill the rest: first the core windows (Claude's
5-hour and weekly, Codex's two windows), which always fit, then scoped extras
such as Fable, shortest window first. The phone and the watch reject a payload
or message that breaks this contract as a whole.
See the [collector guide] for settings, the complete payload schema, retry and
freshness behavior, and deployment assumptions.

## Watch face

The face targets Pebble Time 2 (`emery`). Download the installable `.pbw` from
[GitHub releases], or follow the [watchface guide] to build, configure and install
it. That guide also records the headless-emulator path and release workflow.

![Pebble Time 2 emulator showing quota pace][screenshot]

## Tests and status

From the repository root:

```bash
python3 -m unittest discover -s tests -v
ruff check .
ty check
```

The suite uses synthetic provider responses, fake subprocesses and loopback HTTP
servers; it blocks real provider access. Its watch pipeline tests run the phone
script under Node and compile the watch's message and gauge rules with the host C compiler;
they are skipped when `node` or `cc` is missing. [Ruff] and [ty] run with their default
rules, without project configuration, and report no findings; a `noqa: BLE001`
comment explains each deliberate broad `except`. CI currently builds and checks
the watch bundle but runs neither the suite nor these checks. See the [task
tracker] for completed work and unverified proposals, and the [documentation
review] for this source check's findings. Live deployment and installed Codex CLI
compatibility were not verified by that check.

[collector guide]: docs/collector.md
[GitHub releases]: https://github.com/akaihola/pebble-quota/releases/latest
[watchface guide]: watchface/README.md
[screenshot]: watchface/quota-pace.png
[Ruff]: https://docs.astral.sh/ruff/
[ty]: https://docs.astral.sh/ty/
[task tracker]: TASKS.md
[documentation review]: docs/reviews/2026-10-22-docs-review.md
