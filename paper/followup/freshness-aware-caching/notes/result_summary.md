# Result summary

Status: no new observations collected.

## Prior pilot, excluded from new estimates

The earlier study pilot showed that a fixed TTL reduced origin reads but returned stale content, while a perfect-signal update-aware rule returned fresh content with fewer origin reads than bypass. These findings motivate the new questions but cannot be presented as confirmation in this paper.

## New-study results

Populate only after the protocol, workload sources, trace generator, source lock and analysis code are frozen and the declared collection gate passes.

Current semantic and HTTP tests are engineering checks. They are not study observations and must not be summarized as Results.

Required result anchors:

- Freshness violation rate, revision lag and stale duration by policy and regime.
- Readiness distribution by policy among configurations satisfying the freshness rule.
- Origin reads, CPU, transferred bytes and queueing by policy.
- Transport across applications, traces and hosted allocations.
- Failure inventory and sensitivity to notification delay, loss and reordering.
- Direct comparison with the Mao et al. write-reactive update-or-invalidate rule where the workload supports it.

No learned-policy result belongs in this study. A later learning comparison requires a separate prospective protocol.
