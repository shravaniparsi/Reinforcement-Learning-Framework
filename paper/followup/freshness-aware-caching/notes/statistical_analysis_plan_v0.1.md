# Statistical analysis plan v0.1

Status: pre-collection working plan. No final-test observations have been generated.

## Unit and replication

The independent experimental unit is one complete execution of one frozen policy over one trace on one declared allocation. Requests, updates and notification deliveries within that execution are repeated observations and are aggregated into trace-level outcomes. They are not independent replicates. Policies are paired by workload, regime, trace seed, transport and fault profile. Allocation and execution order are retained as blocking variables.

The final-test seed pool contains 20 seeds per workload and regime. This is an available pool rather than a declared `n`. The final `n` will be chosen once from the variance-planning partition and frozen before any final-test run.

## Outcomes

The primary correctness outcome for each unit is the proportion of requests whose complete served-content hash fails the workload oracle. Additional correctness summaries are total continuous stale residence, maximum revision lag and the proportion of traces with any freshness violation.

Efficiency outcomes are reported separately: readiness or response latency, origin reads, validations, handler CPU, origin response bytes, notification bytes, repair operations and failure proportion. No weighted score combines correctness, latency, CPU and bytes.

## Estimands

For each prespecified workload, regime, transport and fault profile stratum, the basic estimand is the mean paired trace-level difference between two policies. Freshness differences are reported in percentage points. Latency, CPU and byte differences are reported in their original units and as paired ratios when the denominator is positive. The trace, rather than the request, supplies one paired value.

The primary robustness contrast is event invalidation with repair minus always invalidation under the three loss profiles. The primary estimand is the paired difference in freshness-violation proportion. A negative value favors repair.

The primary adaptation contrasts under no fault are write-reactive minus always update and write-reactive minus always invalidate. Freshness is assessed first. Efficiency differences are interpreted only when the upper uncertainty bound for excess freshness violations is no greater than 1 percentage point. Update, invalidation and miss costs for the write-reactive rule use serialized bytes; no subjective weights combine system resources.

All other policy pairs, individual requests and the combined-stress profile are secondary or sensitivity analyses. They cannot replace the primary contrasts after inspection.

## Parameter selection

TTL, stale-window, repair and initial `E[W]` values may be selected only from `parameter_grid_v1.json`. Training traces fit the parameters. Validation traces confirm the locked choice without refitting. Variance-planning traces estimate precision only. Final-test traces cannot change parameters, outcomes, contrasts, fault profiles or sample size.

Parameter selection is lexicographic. First minimize mean trace-level freshness-violation proportion. Among candidates whose mean is within 1 percentage point of the minimum, choose the candidate with fewer mean origin response bytes. If still tied, choose the simpler or shorter candidate in the order declared in the machine-readable grid. This rule does not combine freshness and bytes into a scalar.

## Precision rule

Variance planning uses paired trace-level differences for every primary contrast. The target 99% confidence-interval half-width is 1 percentage point for freshness-violation differences. For byte, CPU and latency outcomes, the target half-width is 10% of the paired reference-policy mean in the same stratum. Required `n` is calculated from the paired standard deviation using `ceil((2.5758293 * s / h)^2)`, where `h` is the target half-width. The final `n` is the largest requirement across primary contrasts and outcomes, with a minimum of 8 independent trace seeds. If the estimated requirement exceeds the reserved pool of 20 seeds, the pool and protocol must be expanded before final-test collection; the study will not stop at 20 and claim the target was met.

The calculation method and interval implementation will be encoded and unit-tested before variance planning. No final-test outcome contributes to the variance estimate or stopping decision.

## Interval and multiplicity policy

There are five primary contrast types: repair versus always invalidation at each of three loss levels, plus write-reactive versus always update and versus always invalidate under no fault. Primary results use 99% percentile bootstrap intervals, equivalent to a Bonferroni familywise level of 0.05 across these five prespecified contrast types. Each interval uses 10,000 deterministic resamples of complete paired trace units, preserving every within-trace request and the policy pairing. Secondary results use 95% intervals and remain descriptive. Workload-stratified estimates will not pool requests across workloads. No significance threshold or star notation will be used.

The primary contrast family is limited to the repair contrast under loss and the two write-reactive contrasts under no fault. Conclusions will be based on effect magnitudes, uncertainty and the prespecified 1-percentage-point freshness margin. Secondary policy pairs and fault profiles will be labeled descriptive; they cannot be promoted because their intervals exclude zero.

## Failures and missing units

The protocol's failure rules operate before analysis. A failed reset, schedule mismatch, missing oracle value or unaccounted request failure invalidates the complete unit. The failed unit and diagnostics remain in the archive. No request-level deletion or passing subset is used. Missing paired units are reported by reason. Re-execution is allowed only under a protocol-defined infrastructure-failure rule and retains both attempts.
