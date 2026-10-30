# Fixed-TTL and SWR training lock

Date: 2026-10-29

GitHub Actions run: `40984591923`

The time-candidate training phase completed all 90 planned blocks and all 4,320
full-trace units without application or infrastructure failure. Every block
contained 42 fixed-TTL or stale-while-revalidate candidates and six matched
controls spanning all eight policy families. The raw compact archive is retained
locally under `data/training/freshness-time-candidates-40984591923/` and occupies
approximately 1.0 GB.

The checksum-bound parameter lock is
`data/training/freshness-time-candidates-40984591923/selected_time_parameters.json`.
It binds 90 manifests, 90 schedules, 4,320 unit artifacts and 4,320 option files.
Selection was performed separately by workload, regime and policy family using ten
independent full-trace units per candidate. The frozen rule first minimized mean
trace-level freshness violations, retained candidates within one percentage point
of that minimum, then minimized mean origin response bytes and used declared order
only for any remaining tie.

| Workload | Regime | Fixed TTL | SWR TTL | SWR stale window |
|---|---|---:|---:|---:|
| Mutable product | Read-heavy | 25 ms | 25 ms | 10 ms |
| Mutable product | Balanced | 25 ms | 10 ms | 10 ms |
| Mutable product | Write-intensive | 25 ms | 10 ms | 10 ms |
| RealWorld feed | Read-heavy | 10 ms | 10 ms | 10 ms |
| RealWorld feed | Balanced | 10 ms | 10 ms | 10 ms |
| RealWorld feed | Write-intensive | 10 ms | 10 ms | 10 ms |
| React-admin dashboard | Read-heavy | 25 ms | 10 ms | 10 ms |
| React-admin dashboard | Balanced | 10 ms | 10 ms | 10 ms |
| React-admin dashboard | Write-intensive | 10 ms | 10 ms | 10 ms |

These are training choices, not confirmatory estimates of policy effectiveness. The
selected training means and all candidate source hashes remain in the machine-
readable lock. Event-repair and write-reactive fitting, validation, variance
planning and final-test collection remain incomplete. Final-test collection is
still prohibited.
