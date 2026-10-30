# Variance-planning and sample-size design

Date: 2026-10-30

The variance-planning partition uses the ten prospectively reserved seeds 300
through 309. It runs all eight locked policies across three workloads, three
request/update regimes, both Redis transports and the four conditions needed for
the five primary contrast types: no fault and 1%, 5% and 10% notification loss.
The frozen campaign contains 720 hosted allocation blocks and 5,760 full-trace
policy units. No parameter or policy may change in this partition.
Every variance block is cryptographically bound to the complete passed validation
report as well as the three training parameter locks.

The independent planning unit is one complete paired trace execution. Requests,
updates and deliveries within a trace are repeated observations and do not
increase `n`. Pairing is performed separately within each workload, regime,
transport, fault profile and seed.

The three robustness contrasts compare event invalidation with repair against
always invalidation at 1%, 5% and 10% loss. The two adaptation contrasts compare
write-reactive against always update and always invalidate under no fault.
Precision is calculated separately for every workload, regime, transport,
contrast and outcome stratum.

Five outcomes drive sample size: freshness-violation proportion, mean request
wall time, operation thread CPU, request-path plus publisher origin-response
bytes and delivered Redis payload bytes. Freshness uses an absolute 99% interval
half-width target of 0.01. Each latency, CPU and byte outcome uses a target equal
to 10% of the reference-policy mean in the same stratum. The calculation is
`ceil((2.5758293035489004 * s / h)^2)` from the standard deviation of ten paired
trace differences, with a minimum of eight final seeds.

The final seed count is the maximum across all 450 prespecified calculations.
If the requirement exceeds the reserved 20-seed final pool, final testing remains
prohibited and the protocol and seed pool must be expanded. No final-test outcome
may contribute to the variance estimate or sample-size decision.
