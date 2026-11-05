# Clustered-loss precision targets v0.1

## Status

This addendum was fixed after the engineering campaign passed and before any precision-planning observations were collected. It governs sample-size planning only. It does not authorize final collection and does not amend or pool observations from the completed freshness study.

## Independent unit and paired structure

The independent unit is the trace seed. Each seed supplies the complete crossed set of three applications, three request/update regimes and two Redis transports. Within each of these 18 strata, all policies and fault profiles share the same exogenous trace. A seed-level estimate first averages the 18 paired stratum contrasts with equal weight. Precision is then estimated across seeds. Requests, updates, policies, profiles and strata within a seed are not counted as independent replicates.

## Prespecified contrasts

The profile contrast is `single-burst-10` minus `dispersed-10` at an equal budget of 10 suppressed update notifications.

The primary policy contrast is evaluated for event invalidation with bounded repair. The policy-by-profile interaction subtracts the corresponding profile contrast for always invalidation from the bounded-repair profile contrast. These two estimands are evaluated for:

1. semantic freshness-violation proportion; and
2. persistence beyond 10 post-fault requests, defined as observed terminal recovery requiring more than 10 post-fault requests or remaining right-censored at the trace boundary.

The persistence endpoint gives every trace a defined binary value without treating a right-censored recovery time as an observed event time. Elapsed recovery time and requests to observed recovery remain reported outcomes, but they do not determine the final seed count under this addendum.

## Precision rule

The precision-planning partition contains 10 seeds, 2100 through 2109. It is disjoint from engineering and final seeds. For each of the four estimands, the planning analysis computes the standard deviation of the 10 seed-level estimates. To reduce the risk of choosing a final campaign from a downward-biased pilot variance, planning uses the one-sided 90% upper confidence bound for the population standard deviation under the usual independent-seed approximation. For each candidate final seed count, the projected two-sided 95% interval width is twice the Student-t critical value multiplied by that upper standard-deviation bound and divided by the square root of the candidate count.

The full-width targets are:

- 0.01 for the bounded-repair freshness profile contrast;
- 0.01 for the bounded-repair versus always-invalidation freshness interaction;
- 0.10 for the bounded-repair persistence profile contrast; and
- 0.10 for the corresponding persistence interaction.

The candidate final seed counts are 12, 18, 24, 30, 36 and 48. The smallest candidate satisfying all four targets is selected. If no candidate satisfies all targets, or if a seed-level variance is exactly zero and therefore cannot support a stable variance estimate, final collection remains unauthorized and the protocol must be revised before any additional data are collected.

## Locked analysis conventions

The analysis requires all 18 strata, both compared profiles and both compared policies for every planning seed. No incomplete seed is admitted. No observations are excluded as outliers. The final analysis will use 10,000 shared trace-seed bootstrap resamples with seed 20261104, preserving all within-seed pairing. The final reserved seed range begins at 2200. A new protocol version must record the selected count and exact terminal seed before final collection can be authorized.
