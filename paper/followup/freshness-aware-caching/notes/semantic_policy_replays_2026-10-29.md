# Cross-workload semantic policy replays

Status: engineering evidence only; no performance observations and no study estimates.

The W1, W2 and W3 gateways replayed source-bound machine-readable schedules through all eight policies. Every policy within a workload received the same event-trace identity and fault-schedule identity. W2 and W3 schedules include a delayed notification, a prompt newer notification, an older notification delivered after the newer revision, a duplicated delivery and a dropped notification.

`F` means the complete response-content hash matched the oracle for that request revision. `S` means the served response was stale.

| Policy | W1 | W2 | W3 |
|---|---|---|---|
| Bypass | FFF | FFFFF | FFFFF |
| Conditional validation | FFF | FFFFF | FFFFF |
| Fixed TTL | FSF | FSFFF | FSFFF |
| Stale-while-revalidate | FSS | FSSFS | FSSFS |
| Always invalidate | FSF | FSFFS | FSFFS |
| Always update | FSF | FSFFS | FSFFS |
| Write-reactive | FSF | FSFFS | FSFFS |
| Event invalidation with repair | FSF | FSFFS | FSFFS |

The patterns are checks of declared mechanics rather than comparative findings. Bypass and conditional validation remain fresh because they contact the origin on every request. Event-driven policies are stale before a delayed notification and after a dropped notification. Always-update and write-reactive carry complete W2/W3 query replacements created at the commit revision. Delivery of the older revision after the newer revision does not regress cached content. The repair policy remains stale in the final request because the request occurs before its declared 25 ms repair age; a separate unit test verifies repair at the boundary.

Publication records retain source-side actions, query-construction origin reads, origin response bytes and serialized notification bytes. The artifacts contain no response latency, readiness or CPU observations.

Artifacts:

- `data/engineering/freshness-w1-policy-replay-v2/results.json`
- `data/engineering/freshness-w2-policy-replay-v1/results.json`
- `data/engineering/freshness-w3-policy-replay-v1/results.json`
