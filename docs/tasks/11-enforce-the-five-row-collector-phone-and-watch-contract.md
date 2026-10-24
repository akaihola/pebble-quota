---
depends-on: [8, 9]
---

# Enforce the five-row collector phone and watch contract

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F7 / Step 7. Phone silently slices to five and ignores v; C numeric
tuples are unchecked and Claude/Fable pair solely by name.

## Acceptance criteria

- Specify deterministic priority/selection for five rows, keeping core Claude/Codex
  windows visible under extra scoped models; separate bounded wire identity from
  arbitrary display names. Reject unsupported versions explicitly.
- Validate required row fields, finite integer ranges and bounded strings in JS;
  reject malformed updates atomically. Validate C tuple type/length and coherently
  replace rows, without stale labels/partial state. Combine Claude/Fable only when
  reset and duration both match; mismatches obey the capacity policy.
- Python/Node/minimal host C fixtures cover 0/1/5/6+ rows, scoped/long names, bad
  versions, missing/wrong fields/tuples and mismatched resets. No schema generator.
- Check message keys against package.json and prove a valid five-row message fits
  2048 bytes. Inspect Emery captures for five unpaired rows and stale status; record
  any missing SDK/emulator prerequisite rather than claiming visual verification.
- Document compatible additions or a deliberate version transition and paired rollback.

## Steward notes, 2026-10-24

Promoted from Unverified proposals by the steward (tier 1: the quota source);
this authorizes the implementation, not a deployment. Confirmed on `main`
(`7e221f5`, after [9]): the collector sends `{"v": 1, "at": …, "q":
rows[:5]}`, the phone script takes `(data.q || []).slice(0, 5)` and never
reads `v`, the watch's `tuple_int()` reads `value->int32` without checking
the tuple's type or length, and `gauges.c` pairs the weekly Claude and Fable
rows by identity alone ("This assumes equal resets").

- Build on [9]'s freshness fields and keep its old-watch compatibility
  (`p` keeps its version 1 meaning). [9] is completed but not yet accepted;
  its receipt is rechecked after this issue, together with this one.
- Five-row priority, unless the code shows a better reason: Claude 5-hour,
  Claude weekly and Codex weekly always get a row; scoped extras (Fable and
  any later one) fill the rest in a stable order. Record the rule in the
  README.
- Keep `latest.json` backward compatible: add fields, never rename or remove
  one or change its meaning. kandev-pacer and the steward's quota line read
  it. A watch with the old bundle must keep working against the new
  collector until Antti installs the new one; if a version change can't be
  avoided, document it with the paired rollback.
- `pebble-quota.service` runs `collector/pebble_quota.py` from this checkout.
  Don't restart it; the steward restarts it after acceptance. Installing on
  the phone or watch is Antti's. Check the watch side on the Emery emulator
  under `xvfb-run` (`watchface/shell.nix`, the installed SDK 4.17, as [9]
  did) and record what each capture shows, or record the missing
  prerequisite. Never claim on-device verification.
- Out of scope: the phone's endpoint and token settings ([6]) and response
  ordering ([14]).
- Keep machine paths out of committed docs and code; the check receipt is
  exempt. A formatting-only change that a required check demands is allowed.
- Size: about 3–4 hours.

## Plan

Checked on `main` at `277d600`. The adapters produce at most four unscoped
windows (Claude's 5h and 7d, Codex's primary and secondary) and one scoped
extra (Fable), so today's payload never exceeds five rows and the slice never
bites. The order still depends on mapping order, which differs between the
immediate `collect` output and the sorted disk snapshot. The phone takes any
`v`, slices to five and forwards rows unchecked. The watch reads integer tuples
without checking type or length, keeps old labels when a string is missing,
and pairs Claude/Fable weekly rows by identity alone.

No wire field changes, so there is no version change and no paired rollback.

### Five gauge lines

The watch has room for five gauge lines, and each provider in `n` takes one.
The collector fills the rest with rows ranked by:

1. core (unscoped) windows before scoped extras;
2. provider: Claude, then Codex;
3. shorter window first, then wire code, then window label.

The core windows are at most four, so Claude 5h, Claude weekly and both Codex
windows always get a row, and scoped extras (Fable, any later one) fill what
is left in a stable order. The chosen rows go out in display order: provider,
core before scoped, duration, code, label. Typical payloads keep today's
order.

### Wire identity

- A table maps each supported Claude model scope's display name to a one-letter
  wire code (`Fable` → `F`). The adapter keeps only scopes in the table, and
  `latest.json` keeps its `7d (Fable)` label.
- One helper turns a snapshot label into `(code, window)`. A Claude label with
  a parenthesised scope that is not in the table is invalid instead of passing
  as a core `C` row. The window stays 1–7 printable ASCII.
- The watch keeps naming known codes itself and shows an unknown code as its
  letter. No display name crosses the wire.

### Phone

Validate the whole payload before building the message; any failure logs the
reason and sends nothing, as a failed request does, so the watch keeps aging
its last valid rows.

- `v` must be exactly 1; `at` an integer in `0..2^31-1`.
- `n` absent or zero to three capital letters; `q` an array with
  `q.length + n.length <= 5`; `t` absent or a 32-bit integer.
- Each row: `s` one capital letter, `w` 1–7 printable ASCII, `u` 0–100, `r`
  0–2^31-1, `d` 1–21,474,836, `o` absent or 0–2^31-1, `e` absent, 0 or 1. The
  phone ignores `p`.

### Watch

- A Pebble-free `decode_message()` in the gauge module takes one field per
  message key (type, length, bytes) and fills a fresh `QuotaMessage`.
  Integers must be INT or UINT tuples of 1, 2 or 4 bytes within the same
  ranges; strings must be NUL-terminated C strings within the same bounds.
  `COLLECTED_AT`, `ROW_COUNT`, `UNAVAILABLE` and all seven fields of each
  counted row are required; `TEMP` is optional. Only a valid message replaces
  the shown state, in one struct assignment.
- Claude and Fable weekly rows share a gauge only when reset and duration both
  match; otherwise Fable gets its own line, which the five-line limit covers.
- With no rows, providers in `n` still show as unavailable.

### Tests and checks

- Python: selection for 0, 1, 5 and 6+ rows with extra scoped models patched
  into the table, with and without an unavailable provider; deterministic
  order whatever the mapping order; long and unknown scope names in the
  adapter and in snapshot labels.
- Node, through the phone harness, which also returns the log: valid 0, 1 and
  5 rows; 6 rows; rows plus `n` over five; versions missing, 0, 2 and `"1"`;
  missing and wrong-typed fields, non-integers, out-of-range values, long and
  non-ASCII strings. Rejections send nothing and log a reason.
- Host C: the driver reads messages as typed tuples on stdin, decodes each,
  and prints the plan of the last accepted one. Fixtures cover wrong types,
  wrong integer lengths, a missing terminator, missing fields, out-of-range
  values, too many lines, atomic rejection after a valid message, mismatched
  resets or durations, 0 rows with `n`, and five unpaired rows. The pipeline
  tests use the same driver.
- Message keys the phone sends and the watch reads equal `package.json`'s
  list, and the largest valid five-row message fits the 2,048-byte inbox by
  the SDK's dictionary size formula.
- Ruff, ty, the full suite, `make clean build`, and Emery captures under
  `xvfb-run` for five unpaired rows and for stale status.

### Docs

[The collector reference] gets the five-line rule, wire identity, the phone
and watch validation, and the compatibility note: old and new collectors and
bundles mix freely, so each rolls back on its own. [The README] states the
five-row rule and [the watchface guide] the pairing and rejection behaviour.

[The collector reference]: ../collector.md
[The README]: ../../README.md
[the watchface guide]: ../../watchface/README.md

## Implementation and verification

Implemented on 2026-10-24 as planned. No wire field or version changed. No
collector restart, deployment, phone install or on-device check was done.

- **Collector** ([collector]): `CLAUDE_SCOPED_CODES` maps supported scope
  display names to wire codes (`Fable` → `F`), and `wire_identity()` turns a
  snapshot label into a bounded `(code, window)`. `normalize_window()` uses it,
  so a Claude label with an unknown parenthesised scope is invalid instead of
  passing as a core `C` row. `compact_watch()` ranks rows (core before scoped,
  provider, duration, code, label), keeps `5 - len(n)` of them and sends them in
  display order. The snapshot keeps its `7d (Fable)` label.
- **Phone** ([phone script]): `quotaMessage()` checks the whole payload and
  throws on the first problem; `refresh()` logs `Rejected quota data:` with
  the reason and sends nothing. It no longer slices.
- **Watch:** [the gauge module] gains `decode_message()`, which fills a
  `QuotaMessage` from one typed field per message key and returns false on any
  missing, mistyped, wrong-length or out-of-range value. [The watch app] reads
  the tuples into those fields, decodes into static scratch space and assigns
  the shown message only on success. Claude and Fable pair only with equal
  reset and duration, and a message with no rows still shows its unavailable
  providers. `MAX_GAUGES` is now five, because the decoder rejects more rows
  plus unavailable providers than that.
- **Docs:** [the collector reference] gains the five-line rule, wire identity,
  the phone and watch checks, the 437-byte message size and the compatibility
  note; [the README] states the rule; [the watchface guide] covers pairing and
  rejection.

[The tests] gain 13 tests (86 → 99):

- `CompactSelectionTests` (Python): 0, 1 and 5 rows in the same order whatever
  the snapshot's mapping order; seven windows with two extra scoped models
  patched into the table, with and without Codex; unknown, long and malformed
  scope labels in the adapter and the snapshot, and a long supported display
  name that reaches the wire only as its code.
- `PhoneContractTests` (Node through [phone harness], which now also returns
  the log): valid 0, 1 and 5 rows; 65 rejected responses (versions missing, 0,
  2 and `"1"`; bad `at`, `n`, `t` and `q`; 6 rows; rows plus `n` over five;
  each required row field missing; wrong types, non-integers, out-of-range
  values, long, empty and non-ASCII strings; unparsable JSON), each sending
  nothing and logging one reason. The keys the phone sends plus
  `REQUEST_SYNC` equal `package.json`'s list, as do the `MESSAGE_KEY_` names in
  the watch app. The largest valid message is 437 bytes by Pebble's dictionary
  layout, within the 2,048-byte inbox.
- `WatchDecodeTests` (host C through [watch driver], which now reads typed
  tuples on stdin): 43 malformed second messages (missing keys, wrong tuple
  types, 8-byte integers, unterminated strings, out-of-range values, too many
  lines) each rejected while the earlier five rows stay as they were; 1-, 2- and
  4-byte signed and unsigned integers and an absent temperature accepted; a
  valid one-row message replacing five rows with no leftovers; pairing only for
  equal reset and duration; five lines including an unavailable provider and
  an unknown code, and 0 rows with and without `n`.
- `WatchPipelineTests`: five unpaired rows end to end when Fable resets apart,
  and extra scoped models through the Claude adapter leaving the healthy
  display unchanged, then taking the line left by a failed Codex.

One existing expectation changed: the sanitisation test served six valid rows,
five of them core, and expected the old mapping-order slice to keep Fable. The
new policy keeps the five core rows.

### Checks before the merge

- `python3 -m unittest discover -s tests -v`: 99 tests pass, none skipped
  (86 existing, one with a changed expectation, and 13 new).
- `ruff check .` and `ty check`: no findings.
- `make clean build` in `watchface`: the bundle builds with SDK 4.17. The
  compiler still warns that the temperature `snprintf` may truncate; only its
  variable name changed. The linker's RWX segment notice comes from the SDK.
- `git diff --check`: clean.

### Emery emulator captures

The emulator ran headless under `xvfb-run` inside [the Nix shell], against a
temporary copy of the bundle whose only change pointed the phone script's
default endpoint and token at a loopback server. That server served
synthetic snapshots through the collector's `Handler` (one scene served a raw
body instead), with no refresher and no provider access. Timestamps were
relative to the capture time, and each scene reinstalled the app.

- **Five unpaired rows** (Fable resetting an hour after Claude weekly): five
  lines, `Claude 5h` green at 20% with `updated 0m ago`, `Claude 7d` green at
  40%, `Fable 7d` red at 70%, `Codex 5h` yellow at 45% and `Codex 7d` green
  at 10%, each with its own marker; 22° and the calendar above. At 18 pixels a
  line the bars shrink to 4 pixels and the titles sit tight above them, but
  nothing overlaps or clips.
- **Stale status** (same rows, Claude kept 40 minutes after a 429): the three
  Claude lines show dark-gray used bars and `stale 40m`; both Codex lines keep
  their pace colours. The temperature stays, because the pass is current.
- **Unsupported version** (the same payload with `v: 2`): the face shows
  `Waiting for quota data`, and the emulator log shows `Rejected quota data:
  unsupported version 2` from the phone script.
- **Paired** (equal resets): four lines with `Claude+Fable 7d` as two bars
  under one marker, as before.

The log showed `Quota data sent` for the valid scenes and no watch-side
`Rejected malformed quota message`, so the emulator's own AppMessage encoding
(32-bit integers, terminated strings) passes the decoder.

Not verified: a physical watch or phone, and the deployed collector. Both
belong to the owner's install and the steward's restart.

### Remaining gaps for the steward

- An unsupported version or malformed payload looks on the watch like a phone
  that stopped delivering: the old rows age to stale. Only the phone log names
  the cause. A visible rejection state would need a new message key.
- Old bundles still pair Claude and Fable by identity alone until the new
  bundle is installed.

### Guarded command resource record

Memory readings are in MiB. Each guarded command ran alone through a wrapper
that waited for 2,048 MiB available (10-minute limit, 1,536 MiB fallback). It
stopped the command below 1,024 MiB available or after 512 MiB of swap growth.

- `make -C watchface clean build`, first attempt: **started at once**; wait
  0 s; admission 9698, final 9711; starting swap 846, growth 0; 1 s; exit 2.
  The sandbox kept the Pebble tool from writing its settings file; the rerun
  outside the sandbox followed.
- `make -C watchface clean build`: **started at once**; wait 0 s; admission
  9700, final 10582; starting swap 846, growth 0; 2 s; exit 0.
- `make build` of the temporary capture bundle: **started at once**; wait 0 s;
  admission 9749, final 9663; starting swap 846, growth 0; 1 s; exit 0.
- Emulator captures (`nix-shell watchface/shell.nix --run 'xvfb-run -a
  python3 <capture script>'`): **started at once**; wait 0 s; admission 9834,
  final 10350; starting swap 846, growth 24; 48 s; exit 0.
- Full suite, final run (`python3 -m unittest discover -s tests -v`):
  **started at once**; wait 0 s; admission 10605, final 10571; starting swap
  870, growth 0; 15 s; exit 0.

Two development runs of the full suite (about 11 and 14 seconds) ran without
the wrapper, with 10,349 and 9,943 MiB available at the last readings before
them; their swap was not measured. Ruff, ty, focused test runs and host
compiles ran unguarded; each takes seconds.

[collector]: ../../collector/pebble_quota.py
[phone script]: ../../watchface/src/pkjs/index.js
[the gauge module]: ../../watchface/src/c/gauges.c
[The watch app]: ../../watchface/src/c/watchface.c
[The tests]: ../../tests/test_pebble_quota.py
[phone harness]: ../../tests/watch/phone.js
[watch driver]: ../../tests/watch/gauges_main.c
[the Nix shell]: ../../watchface/shell.nix
