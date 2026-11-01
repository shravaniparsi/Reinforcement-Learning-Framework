# Full manuscript claim audit, 2026-10-31

## Scope

Audited the Journal of Grid Computing submission source at commit `31f31bc`:

- `submission/journal-of-grid-computing/upload/manuscript.tex`
- `submission/journal-of-grid-computing/upload/references.bib`
- `submission/journal-of-grid-computing/journal-of-grid-computing-manuscript.pdf`

The audit covered numerical results, protocol and implementation statements,
statistical reporting, literature-backed claims, repository and DOI statements,
and PDF layout. It did not treat the manuscript's bounded discussion and
recommendations as universal claims beyond the stated experimental conditions.

## Outcome

- No unsupported central result or numerical mismatch was found.
- All reported numerical ranges and interval counts were independently
  recomputed from the released 450-row primary-estimate table.
- The frozen design, analysis JSON, source code and workflow support the stated
  sample size, pairings, execution count, runtime, fault schedules, process
  isolation, policy ordering and bootstrap procedure.
- The primary literature supports the cited background claims within the
  manuscript's wording.
- One definite bibliography metadata error and two minor wording risks remain.

## Verified empirical claims

The released analysis contains 450 primary estimates, each with 67 complete
paired trace units and 10,000 bootstrap resamples. It records 4,824 allocation
blocks, 38,592 full-trace policy executions and 86,832 source files. Independent
recomputation confirmed:

- repair versus invalidation freshness ranges at 1%, 5% and 10% loss;
- all stated confidence-interval sign counts;
- request-time and CPU ranges for repair;
- zero Redis-payload difference for the repair contrasts;
- exact zero freshness differences for the 36 no-fault write-reactive
  comparisons;
- write-reactive request-time, Redis-payload, CPU and origin-byte ranges and
  workload splits against fixed update;
- write-reactive interval counts and byte ranges against fixed invalidation;
- all 90 freshness comparisons passing the prespecified admissibility rule.

The repository result tables are byte-identical to the tables in the published
Zenodo core archive. The Zenodo core ZIP also has the same SHA-256 digest as the
GitHub release asset.

## Verified design, implementation and statistical claims

- Trace design: 100 updates; 500, 200 and 100 requests in the three regimes;
  5--15 ms logical inter-event gaps.
- Disjoint seed ranges: engineering 0--1, training 100--109, validation
  200--204, variance planning 300--309 and final test 1000--1066.
- Primary faults: exact loss of 0, 1, 5 or 10 of 100 notifications.
- Runtime: GitHub Actions `ubuntu-24.04`, Python 3.9.25 and Redis 7.0.15;
  workflow `max-parallel: 3`.
- Allocation: deterministic SHA-256-derived policy permutation based only on
  block identity.
- Isolation: every policy is launched as a new subprocess; workload, cache and
  transport state are reset; each unit starts an isolated Redis server bound to
  `127.0.0.1` on a free port.
- Sample size: 450 prospective precision calculations over ten variance-planning
  pairs produced a maximum requirement of 67 final-test seeds, followed by the
  recorded protocol expansion from the initially reserved 20-seed pool.
- Analysis: paired differences are formed on common trace seeds; 99% percentile
  intervals use 10,000 deterministic resamples of complete paired trace units.
  The manuscript correctly avoids a simultaneous familywise-coverage claim.

Eight frozen contract tests for final design, final analysis, locked execution
and measurement passed during this audit.

## Verified literature and external-resource claims

- RFC 9111 supports the freshness, staleness and conditional-validation claims.
- RFC 5861 supports stale serving during background revalidation.
- Cao and Liu support the invalidation-versus-polling comparison as worded.
- Alici et al. and Sazoglu et al. support timestamp- and workload-based result
  cache policies.
- Cho et al. support deep reinforcement learning for TTL utility control under
  changing request conditions.
- Ji et al. support database-assisted precise invalidation of query caches.
- Mao et al. support the cost comparison used for the update-or-invalidate rule.
- Official Redis documentation supports Pub/Sub at-most-once delivery and
  Streams persistence, acknowledgment and recovery.
- Both pinned upstream application commits resolve on GitHub.
- DOI `10.5281/zenodo.23843162` resolves to the released study package, and the
  GitHub release contains the declared core, checksum and raw-archive assets.

## Findings to correct before submission

### Definite metadata error

The title in `upload/references.bib` for DOI `10.5281/zenodo.23843162` is
`Freshness-Aware Caching Controlled Study: Analysis and Reproducibility Package`.
The published Zenodo title is `Cache Freshness under Lost Invalidation Messages:
Confirmatory Data and Reproducibility Package`. The BibTeX title should match the
published record.

### Minor wording risks

1. `eight established cache policies` is broader than necessary because the
   exact bounded-repair combination and write-reactive implementation are
   study-defined adaptations. `eight cache policies` is fully supported.
2. `three independently implemented mutable applications` could be read as
   independently developed by unrelated teams, although two workloads adapt
   pinned upstream applications. `three distinct mutable applications` is more
   precise.

These wording points do not invalidate the findings. They are recommended
credibility edits that preserve the scientific meaning.

### Resolution

All three findings were corrected in the active manuscript, submission metadata,
cover letter and bibliography on 2026-10-31. Historical frozen protocols were
not rewritten.

## Layout finding

The PDF is A4 and the manuscript does not override page geometry. The wide,
slightly asymmetric margins come from the supplied Springer `sn-jnl.cls`
single-column layout: 26 mm top margin, a 31-pica text width, 194.25 mm text
height and a 6 mm binding offset. The margins should not be manually changed
unless the journal requests a different template or review format.
