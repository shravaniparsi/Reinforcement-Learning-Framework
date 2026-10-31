# Confirmatory final-test design lock

Date frozen: 2026-10-30

Protocol v0.5 authorizes one confirmatory campaign after completion of training, held-out validation and variance planning. The variance-planning rule required 67 complete paired traces per stratum. The original 20-seed reserve was insufficient, so only the untouched final-test range was expanded to seeds 1000 through 1066. No final-test observations informed this decision.

The campaign crosses three workloads, three workload regimes, four primary fault conditions, two Redis transports and 67 seeds. Each of the resulting 4,824 matched blocks executes all eight frozen policies in a deterministic randomized order, yielding 38,592 full-trace policy units. The four confirmatory conditions are no fault and notification loss at 1%, 5% and 10%. Delay, duplication, reordering and combined-stress validation observations remain secondary evidence.

One complete policy execution over one trace is the independent experimental unit. Requests within a trace are repeated observations, not independent replicates. The primary analysis contains five prespecified policy contrasts and five prespecified outcomes in every workload, regime and transport stratum, for 450 estimates. Each estimate is a paired mean difference with a deterministic 99% percentile bootstrap interval from 10,000 trace-level resamples. P values and significance stars are not reported. The intervals are per-estimand uncertainty intervals and are not claimed to provide simultaneous familywise coverage across all 450 estimates.

Efficiency outcomes are interpreted only when the upper 99% interval bound for excess freshness violations is at most 0.01. The source locks, policy parameters, workloads, fault schedules, outcomes, contrasts, analysis implementation and 67-seed sample size cannot change after confirmatory collection begins. Application, oracle and schedule failures are retained and are not silently replaced. One replacement allocation is permitted only for a declared infrastructure failure, with both attempts retained.
