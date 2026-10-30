# Variance-planning and sample-size lock

Date: 2026-10-30

GitHub Actions run: `41131844320`

The variance-planning campaign completed all 720 planned allocation blocks and
all 5,760 full-trace policy units without application or infrastructure failure.
It covered the ten prospectively reserved planning seeds 300 through 309, three
workloads, three request/update regimes, both Redis transports and the no-fault,
1% loss, 5% loss and 10% loss conditions required by the primary contrasts.
Every block was bound to the passed validation report and all three immutable
training locks.

The 720 raw GitHub artifacts are retained as individually compressed ZIP files
under `data/variance/freshness-variance-41131844320-archives/`. The archive
occupies approximately 97 MB. `archive_inventory.json` records the GitHub
artifact ID, compressed size and SHA-256 digest for every ZIP. All 720 archives
have distinct digests and passed exact file-count and CRC checks.

The checksum-bound planning report is
`data/variance/freshness-variance-41131844320-archives/final_sample_size_lock.json`.
It binds 720 manifests, 720 schedules, 5,760 unit artifacts and 5,760 policy
option files, for 12,960 source-file hashes. The final requirement is the maximum
of 450 prespecified calculations, each based on ten paired full-trace units.

| Precision outcome | Maximum required final seeds | Median requirement |
|---|---:|---:|
| Freshness-violation proportion | 67 | 8 |
| Mean request wall time | 40 | 8 |
| Operation thread CPU | 23 | 8 |
| Total origin-response bytes | 17 | 8 |
| Delivered Redis payload bytes | 17 | 8 |

The locked final requirement is 67 independent seeds. The driver was the repair
minus always-invalidate freshness contrast under 10% notification loss for the
mutable-product write-intensive regime. In both transport strata, the ten paired
differences had mean -0.04 and standard deviation 0.0316228; the frozen absolute
half-width target was 0.01. The same requirement in both transports reflects the
matched deterministic fault schedule and policy behavior rather than two pooled
sets of replicates.

The reserved final-test pool contains only 20 seeds and is therefore
insufficient. This is a planned protocol-expansion outcome, not permission to cap
the study at 20 or relax the precision target after observing variability. Final
testing remains prohibited. Before collection, a new frozen protocol version
must expand the disjoint final-test seed pool to at least 67 and define a feasible
batched execution plan without changing policies, contrasts, outcomes or the
sample-size rule.
