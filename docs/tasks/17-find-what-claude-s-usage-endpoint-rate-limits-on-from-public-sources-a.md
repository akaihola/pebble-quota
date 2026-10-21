Steward issue, 2026-10-21 14:00 tick. Goal: agentic-leverage (pebble-quota is tier 1 in `<steward-vault>/Goals.md`). Estimated 1 h. Research only.

[2] (back off on HTTP 429 from Claude's usage endpoint) waits in the review queue: its backoff tests pass, but its research never established what the provider keys its throttling on (token, account or address). Source: the steward's triage of the review queue, `<steward-vault>/notes/2026-10-21-left-to-antti-triage.md`, "Prepare the specific repairs", item "Pebble rate-limit backoff".

## Work

1. Read what reliable public documentation says about that endpoint's limits.
2. Read sanitized existing records: this collector's logs of 429 responses, and the steward's `quota.jsonl` (`<steward-vault>/quota.jsonl`), whose `errors` field records them with timestamps. Compare their timing with the collector's polling interval.
3. Write the answer into [2]'s task file as a dated note with sources, and state what stays uncertain. If the requirement can't be met, propose a precise scope correction instead.

## Acceptance

- A sourced answer or a precise scope correction in [2]'s task file.
- No requests beyond the collector's normal schedule; never exhaust a live credential to find the limit. No code change.

## Plan

1. Review official rate-limit documentation and firsthand public reports for
   the exact OAuth usage endpoint; distinguish observations from guarantees.
2. Read existing collector journal records and the steward quota history,
   emitting only timestamps, status counts and scheduling evidence. Make no
   live provider requests and read no credentials.
3. Add a dated, sourced note to [the backoff task] with timing comparisons,
   remaining uncertainty and a precise scope correction if the throttle key
   cannot be established. Validate the documentation, merge locally, and
   complete this research issue pending acceptance.

[the backoff task]: 2-back-off-on-http-429-from-claude-s-usage-endpoint-and-keep-the-last-re.md

## Outcome, 2026-10-21

Added the dated research note and precise scope correction to [the backoff
task]. Public reports conflict about token versus account/IP throttling;
reviewed official documentation gives no contract for this endpoint. The
steward history contains 43 samples, nine with Claude 429 errors, but lacks
request identities and attempt timestamps. The retained collector journal
has only a service-start entry. These records cannot establish the key or a
safe numeric polling allowance. The note distinguishes saved errors from
new requests and compares the observations with the five-minute refresh and
10–60-minute backoff.

The research acceptance is met by the explicit scope-correction alternative;
the original requirement to identify the key remains unverified. The backoff
issue remains pending acceptance. No code, credential, service or provider
schedule was changed; no live provider requests were made.

Validation: all 43 history lines parsed; timestamps and error counts checked;
relative documentation links and `git diff --check` passed. No tests run for
this documentation-only change.

The journal scan was the only guarded heavy command: **started at once**,
wait 0.00s, admission MemAvailable 3434 MiB, final 3436 MiB, initial swap use
2147 MiB, maximum swap growth 0 MiB, elapsed 0.30s, exit 0. JSON records were
streamed; only whitelisted timestamps and categories were retained.
