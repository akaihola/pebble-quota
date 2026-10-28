# Reset-grant runtime evidence recovery

**Cause unresolved.** The bounded October 28 investigation recovered the
original worker's timestamped success summary, but no continuous
restart-to-verdict window or causal discriminator. The [reset-grant delivery]
remains held under the [independent recheck]; completing [this investigation]
does not change that verdict. All times below are UTC.

## Available evidence

- **Saved implementation summaries:** the deployment marker is
  `2026-10-26T17:01:51.659138Z`. A verification saved at
  `2026-10-26T17:12:27.545819Z` records collector attempt/success at
  `2026-10-26T17:11:52.541622Z`, quota and grant metadata available, and null
  retry/stale/failure fields. These are mutable worker summaries, not raw
  service-start events or a complete request trace. Their hashes and safe
  extraction commands are in [this investigation].
- **User journal:** both unit selectors return 115 records from
  `2026-10-28T09:53:57.778418Z` to `2026-10-28T19:26:14.544241Z`:
  **107 requests = 99 ok + 8 HTTP 429**, plus **8 retry_at skips**. No other
  outcomes, uninstrumented lines or service events occur in this retained
  selection. Maximum observed request-log gap: 602.437567 seconds.
- **Quota series:** [the steward series] has 285 lines overall. Within the
  requested October 25–28 verdict window, 128 samples run from October 25
  00:12:01 to October 28 19:08:07: **112 without a Claude error and 16 with
  HTTPError**. All 128 retain Claude windows. None specifies HTTP status 429.
  These are snapshot samples, not request outcomes. A staged copy has 94
  overlapping samples (87 without an error, seven with HTTPError); do not add
  the two series. Nearby samples show HTTPError at October 26 16:49:13
  (collection 16:45:01) and no error at 17:37:56 (collection 17:36:58).
- **Saved checks:** the delivery records 108 offline tests. The independent
  recheck's [saved receipt] verifies 118 tests, focused grants/backoff, Ruff,
  ty, whitespace, scope and revert at `75dec32`; its historical
  `journal-coverage` check fails explicitly. Collector code/tests have not
  changed since that recheck. No suite was rerun.

## Missing evidence and inventory limits

The requested historical interval starts at the reported October 26 17:01:51
restart and ends at the October 28 19:27:23 verdict. Journal queries widened
only the lower bound to October 25 00:00:00. The two readable user journal files
cover October 28 09:53:28–20:11:21 at inventory time; the current service start
at 09:03:47 is also missing. The runtime journal directory is empty. The system
journal exists but is unreadable; ordinary access and one noninteractive sudo
attempt failed. Its coverage is **unknown**, not absent. No explicit retention
limits were found in the inspected system configuration and drop-in locations;
that does not establish effective defaults or the cause of missing history.

The filename inventory checked only direct entries in the four directories
specified in [this investigation]. It found the earlier reader, aggregate
summaries and recorder logs, but no identified raw collector journal export.
The earlier [pacer investigation] preserves seven October 26 and 143 October 27
journal-message counts, mostly generic persistence/refresh errors; these do
not recover Claude request outcomes.

The collector state directory contains only the current snapshot, successful
at October 28 20:06:23; the repository's old snapshot is from August 2. Neither
fills the historical gap. The current pacer event file has 1,233 records from
October 25 22:11:04 to October 28 20:07:27 and no quota/provider/poll event kind;
older rotations were inventoried by metadata only. No private transcripts,
credential files, unrelated content, remote hosts or wider filesystem trees
were searched. Later successful state is not replacement historical coverage.

## Causal assessment

- **Observation:** eight upstream HTTP 429 responses survive in the October 28
  journal; earlier sampled HTTPError states lack status codes.
- **Proposed cause:** parameter-sensitive limiting remains a hypothesis.
- **Normal comparison (inference):** collector source implies the successful
  requests used the same query. They rule out a deterministic malformed query; the samples around deployment
  differ in time and workload and are not controlled request comparisons.
- **Strongest alternative:** upstream limiting, cadence and concurrent callers
  fit the observations; no account-wide request trace survives here.
- **Refuting check:** the diff adds no request and changes no retry scheduling.
  The 99 successes contradict deterministic rejection, not every rate-limit
  effect. No paired control or provider-side explanation was recovered.
- **Order in time:** the deployment marker precedes the retained 429s. Generic
  HTTPError samples also predate it; neither establishes when 429 frequency
  changed or why.
- **Conclusion:** **Cause unresolved**: missing complete request coverage and
  a discriminator holding cadence, callers and upstream conditions comparable.
  Historical recovery is partial; this bounded readable inventory cannot answer
  the causal question. The original hold remains. No owner restart or provider
  choice is needed; any live experiment or retention change needs separate scope.

[reset-grant delivery]: ../tasks/30-include-claude-reset-grants-in-quota-snapshots.md
[this investigation]: ../tasks/32-recover-retained-runtime-evidence-for-reset-grant-snapshots.md
[independent recheck]: http://hopeli/my-knowledge/agents/steward/log/2026-10-28-quiet-repo-rechecks.md?f#collector-journal-and-attribution
[saved receipt]: http://hopeli/my-knowledge/agents/steward/log/2026-10-28-quiet-repo-rechecks.evidence.json?f
[the steward series]: http://hopeli/my-knowledge/agents/steward/quota.jsonl?f
[pacer investigation]: http://hopeli/prg/kandev-pacer/docs/tasks/205-keep-using-claude-s-last-good-pebble-reading-for-up-to-15-minutes-afte.md?f#collector-journal-investigation
