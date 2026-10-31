# Result summary

Status: confirmatory collection and frozen primary analysis complete.

## Evidence population

GitHub Actions run `41148624728` completed all 4,824 matched allocation blocks. The campaign contains 38,592 full policy executions across three workloads, three request/update regimes, four primary fault conditions, two Redis transports and 67 untouched final-test seeds. The frozen analyzer verified 86,832 source files and produced 450 prespecified estimates. Each estimate uses 67 complete paired trace units and a deterministic 99% percentile bootstrap interval from 10,000 resamples. No P values or significance stars are reported, and the intervals are not presented as simultaneous familywise coverage.

The analyzer initially stopped before calculating an estimate because persisted JSON represents `duplicate_delays_ms` as a list while the generator retains the same value as a tuple in memory. The canonical schedule, trace and fault hashes matched. The JSON-normalization correction and its pre-analysis timing are recorded in `notes/final_analysis_verifier_amendment_2026-10-31.md`.

## North Star and claim architecture

**Broad problem.** Cache reuse for mutable application data must reduce work without returning semantically outdated responses when update notifications fail.

**Central question.** Do bounded repair and write-reactive update-or-invalidate selection improve the freshness-efficiency tradeoff over fixed event-driven policies across distinct web workloads?

**Main claim.** Bounded repair consistently reduces freshness violations caused by lost notifications, with a measurable request-time and CPU cost, whereas write-reactive selection preserves freshness but shifts costs among origin work, notification traffic and request time without dominating either fixed update or fixed invalidation.

**Contribution type.** Prospective empirical software-systems study.

**Boundary conditions.** The claim applies to three controlled applications, bounded synthetic traces, no-fault and 1%, 5% and 10% notification-loss conditions, Redis Pub/Sub and Streams, and the frozen policy implementations. A complete policy execution over one trace is the independent unit.

## Confirmatory findings

### Bounded repair reduces violations as notification loss rises

Repair minus always invalidation reduced mean freshness-violation proportions in every evaluated stratum. The reductions ranged from 0.090 to 0.699 percentage points at 1% notification loss, 0.851 to 3.600 points at 5% loss and 1.478 to 7.654 points at 10% loss. The 99% interval was below zero in 17 of 18 strata at 1% loss and all 18 strata at both 5% and 10% loss. The direction was reproduced across all workloads, regimes and both Redis modes.

The freshness gain had a consistent request-time cost. Repair increased mean request wall time by 6.6 to 120.6 microseconds at 1% loss, 6.8 to 124.5 microseconds at 5% loss and 7.6 to 131.2 microseconds at 10% loss. All 54 corresponding 99% intervals were above zero. Thread CPU per trace increased by 0.47 to 65.28 milliseconds; 53 of 54 intervals were above zero and one included zero. Additional origin-response bytes rose with the number of lost messages, while delivered Redis payload bytes were identical to always invalidation in all 54 strata.

### Write-reactive selection preserves freshness but does not dominate fixed policies

Under no injected fault, write-reactive selection and both fixed event policies had identical freshness-violation proportions in all 36 primary comparisons. This authorized interpretation of every prespecified efficiency contrast.

Relative to always update, write-reactive selection increased mean request wall time in all 18 strata by 5.5 to 306.5 microseconds, with every 99% interval above zero. It reduced delivered Redis payload by 19.2 to 1,759.1 KiB per trace in every stratum. CPU and origin-response effects depended on workload: both were lower in the 12 article-feed and dashboard strata and higher in the six product strata. Every CPU and origin-byte interval excluded zero. The rule therefore avoided large query-complete updates for the two complex-query workloads, but the resulting invalidation and miss path increased request time.

Relative to always invalidation, write-reactive selection reduced origin-response bytes only for the six product strata, by 0.84 to 1.90 KiB per trace, and matched invalidation exactly for the other 12 strata. It added 5.9 to 11.9 KiB of Redis payload in every stratum. Request-time intervals were above zero in seven strata, below zero in one and included zero in ten. CPU intervals were above zero in seven, below zero in five and included zero in six. These mixed effects do not support a general efficiency advantage over fixed invalidation.

## Display-item plan

**Figure 1 claim:** bounded repair reduces freshness violations under notification loss while increasing request time. The six panels show paired mean differences and 99% intervals for freshness and request wall time at 1%, 5% and 10% loss. Color identifies workload; marker shape identifies Redis transport.

**Figure 2 claim:** write-reactive selection shifts costs without a universal fixed-policy gain. The eight panels show paired mean differences and 99% intervals for request wall time, thread CPU, origin-response bytes and Redis payload against always update and always invalidation. Freshness differences are exactly zero in every displayed stratum and are stated in the legend rather than plotted as eight redundant zero panels.

Exact estimates are in `output/results/primary_estimates.csv`; contrast-level ranges and interval directions are in `output/results/primary_contrast_summary.csv`.

## Prior pilot, excluded from new estimates

The earlier 60-request pilot motivated the study but did not contribute to fitting, sample-size planning, confirmatory estimation or the findings above.
