# Training serialized-byte cost lock

Date: 2026-10-29

GitHub Actions run: `40982405656`

Phase 1 completed all 90 planned workload, regime and training-seed blocks. Each
block ran all eight policy families in a deterministic identity-bound order. All
720 full-trace units completed without application or infrastructure failure. The
raw download is retained locally under
`data/training/freshness-costs-40982405656/` and occupies approximately 875 MB.

The checksum-bound cost artifact is
`data/training/freshness-costs-40982405656/locked_costs.json`. It covers 90
manifests, 90 schedules and 720 unit artifacts. Update and invalidation costs are
median delivered Redis envelope bytes. Miss costs are median origin response bytes
from bypass fetches. These quantities are training inputs for the write-reactive
rule, not confirmatory study outcomes.

| Workload | Regime | Update bytes | Invalidation bytes | Miss bytes |
|---|---:|---:|---:|---:|
| Mutable product | Read-heavy | 367 | 91 | 141 |
| Mutable product | Balanced | 367 | 91 | 141 |
| Mutable product | Write-intensive | 367 | 91 | 141.5 |
| RealWorld feed | Read-heavy | 17,468 | 196 | 5,342 |
| RealWorld feed | Balanced | 17,464 | 196 | 5,340 |
| RealWorld feed | Write-intensive | 17,464 | 196 | 5,343 |
| React-admin dashboard | Read-heavy | 1,909 | 122 | 1,343 |
| React-admin dashboard | Balanced | 1,909 | 122 | 1,343 |
| React-admin dashboard | Write-intensive | 1,909 | 122 | 1,343 |

For each workload-regime group, update and invalidation medians use 1,000 delivered
messages from ten independent trace units per policy. Miss medians use 5,000,
2,000 or 1,000 responses for read-heavy, balanced or write-intensive regimes,
respectively, again nested within ten independent trace units. Message and request
counts are descriptive cost observations and are not treated as independent
replicates for policy inference.

The large RealWorld update envelope is a direct consequence of the declared
cache-aware complete-query snapshot baseline. It should not be described as a
latency result or generalized beyond this workload and message construction rule.

Candidate fitting and validation have not yet run. Final-test collection remains
prohibited.
