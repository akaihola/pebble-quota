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
