# Event-policy training lock

Date: 2026-10-30

GitHub Actions run: `41006126071`

The event-candidate training phase completed all 720 planned blocks and all
12,960 full-trace units without application or infrastructure failure. Each
block contained 12 candidates across the write-reactive and event-repair
families plus six matched controls. Fitting covered three workloads, three
request/update regimes, four notification-fault profiles, two Redis transports
and ten training seeds.

The 720 raw GitHub artifacts are retained as individually compressed ZIP files
under
`data/training/freshness-event-candidates-41006126071-archives/`. The archive is
approximately 223 MB. `archive_inventory.json` records the GitHub artifact ID,
compressed size and SHA-256 digest of every ZIP. All 720 archives have distinct
digests and passed ZIP integrity checks.

The checksum-bound parameter lock is
`data/training/freshness-event-candidates-41006126071-archives/selected_event_parameters.json`.
It binds 720 manifests, 720 schedules, 12,960 unit artifacts and 12,960 option
files, for 27,360 source-file hashes. Selection was performed separately by
workload, regime and policy family. Each candidate was evaluated on 80
independent full-trace units: four fault profiles, two transports and ten seeds.
The frozen rule first minimized mean trace-level freshness violations, retained
candidates within one percentage point of that minimum, then minimized mean
request-path plus publisher origin response bytes and used declared order only
for any remaining tie.

| Workload | Regime | Repair age | Initial expected writes |
|---|---|---:|---:|
| Mutable product | Read-heavy | 50 ms | 0.25 |
| Mutable product | Balanced | 25 ms | 0.25 |
| Mutable product | Write-intensive | 50 ms | 0.25 |
| RealWorld feed | Read-heavy | 25 ms | 0.5 |
| RealWorld feed | Balanced | 25 ms | 0.5 |
| RealWorld feed | Write-intensive | 25 ms | 0.5 |
| React-admin dashboard | Read-heavy | 25 ms | 1.0 |
| React-admin dashboard | Balanced | 25 ms | 1.0 |
| React-admin dashboard | Write-intensive | 25 ms | 1.0 |

These are training choices, not confirmatory estimates of policy effectiveness.
The selected training means and all source hashes remain in the machine-readable
lock. Validation must confirm the locked choices without refitting. Variance
planning and the sample-size lock must then complete before final-test collection
is authorized.
