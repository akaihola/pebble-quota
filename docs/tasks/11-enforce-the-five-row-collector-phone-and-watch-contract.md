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
