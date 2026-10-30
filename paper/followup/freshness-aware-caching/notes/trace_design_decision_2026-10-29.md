# Prospective trace design decision

The confirmatory study will use bounded synthetic request and update traces generated before outcome collection. Public cache traces were considered but rejected for the core estimand because they do not preserve the complete W1-W3 query content, origin revision, notification identity and browser-visible semantic state required by the independent freshness oracle. The study will not claim that the synthetic traces estimate production prevalence.

Each trace contains exactly 100 origin updates. The three declared regimes differ only in request count:

| Regime | Requests | Updates | Request:update ratio |
|---|---:|---:|---:|
| Read-heavy | 500 | 100 | 5:1 |
| Balanced | 200 | 100 | 2:1 |
| Write-intensive | 100 | 100 | 1:1 |

The first event is a request so event-driven policies can exercise an existing cache entry. Remaining request and update positions are shuffled deterministically within the selected partition seed. Inter-event gaps are bounded from 5 to 15 logical milliseconds. W1 uses an explicit 80/20 hot/cold product mixture. W2 rotates complete feed queries and mutations of existing articles. W3 rotates order, review and customer queries and valid resource updates.

Exactly 100 updates makes each declared fault percentage an integer notification count. The primary engineering design contains the following profiles:

- no injected fault;
- delay of 1, 10 or 100 ms;
- loss of 1, 5 or 10 notifications;
- duplication of 1 or 5 notifications;
- reversal of 1 or 5 non-overlapping adjacent update pairs; and
- combined stress with 10 ms base delay, 5 losses, 5 duplicates and 5 reordered pairs.

Single-factor profiles identify the mechanism. The combined profile checks interaction under one prespecified stress condition. The design is not a full factorial. Dropped notifications are never also duplicated. Reordering is materialized by delaying the earlier update past its selected adjacent successor, and the schedule retains the resulting delivery identity.

Engineering, training, validation, variance-planning and final-test seed ranges do not overlap. The final-test range is a reserved seed pool, not a commitment to use all 20 seeds. The precision rule will determine the number of final traces before final-test collection. Final-test traces must not be executed to choose policies, thresholds or sample size.

The machine-readable design is `experiments/freshness/trace_design_v1.json`. The generator validates partition membership, exact event counts, exact fault counts and deterministic identities.
