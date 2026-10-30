# Held-out validation lock

Date: 2026-10-30

GitHub Actions run: `41099780817`

The held-out validation campaign completed all 1,080 planned allocation blocks
and all 8,640 full-trace policy units without application or infrastructure
failure. It covered three workloads, three request/update regimes, all 12 frozen
fault profiles, both Redis transports and the five prospectively reserved
validation seeds 200 through 204. Every policy options file exactly matched its
checksum-bound training lock; no parameter was refitted.

The 1,080 raw GitHub artifacts are retained as individually compressed ZIP files
under `data/validation/freshness-validation-41099780817-archives/`. The archive
occupies approximately 145 MB. `archive_inventory.json` records the GitHub
artifact ID, compressed size and SHA-256 digest for every ZIP. All 1,080 archives
have distinct digests and passed exact file-count and CRC checks.

The checksum-bound validation report is
`data/validation/freshness-validation-41099780817-archives/validation_report.json`.
It binds 1,080 manifests, 1,080 schedules, 8,640 unit artifacts and 8,640 policy
option files, for 19,440 source-file hashes.

All 36 prespecified workload, regime and fitted-policy guardrails passed. The
largest validation-minus-training increase in mean trace-level freshness
violations was 0.007, below the frozen 0.01 limit. The largest increase within
each fitted policy family was:

| Policy | Maximum increase | Workload and regime | Validation units |
|---|---:|---|---:|
| Fixed TTL | 0.00500 | Mutable product, write-intensive | 5 |
| Stale-while-revalidate | 0.00700 | Mutable product, write-intensive | 5 |
| Event invalidation with repair | 0.00300 | React-admin dashboard, write-intensive | 40 |
| Write-reactive | 0.00585 | RealWorld feed, read-heavy | 40 |

These checks are progression guardrails rather than confirmatory estimates of
policy effectiveness. Validation passing authorizes the frozen policies to enter
variance planning. The variance-planning partition may estimate trace-level
variability and determine the final sample size, but it may not alter policies or
parameters. Final-test collection remains prohibited until the sample-size lock
is complete.
