# Data dictionary

## Primary-estimate table

Each row in `primary_estimates.csv` is one prespecified paired contrast for a
single workload, request/update regime, Redis transport, fault profile and
outcome. A complete policy execution over one trace is the independent unit.

| Field | Definition | Unit or values |
|---|---|---|
| `workload` | Mutable application identity | `mutable-product-v1`, `svelte-realworld-feed-v1`, `react-admin-dashboard-v1` |
| `regime` | Request/update mix | `read-heavy`, `balanced`, `write-intensive` |
| `transport` | Redis delivery implementation | `redis-pubsub`, `redis-streams` |
| `fault_profile` | Injected notification treatment | `no-fault`, `loss-1pct`, `loss-5pct`, `loss-10pct` |
| `contrast_id` | Prespecified treatment-minus-reference comparison | Five protocol-defined contrast types |
| `treatment` | Treatment policy | Policy identifier |
| `reference` | Reference policy | Policy identifier |
| `outcome_id` | Measured outcome | One freshness or four efficiency outcomes |
| `estimate` | Mean paired treatment-minus-reference difference | Outcome's native unit |
| `lower`, `upper` | Deterministic percentile-bootstrap interval limits | Outcome's native unit |
| `confidence` | Interval coverage level for the individual estimand | 0.99 |
| `n` | Complete paired trace units | 67 |
| `resamples` | Complete-pair bootstrap resamples | 10,000 |
| `paired_mean_ratio` | Mean within-pair treatment/reference ratio when defined for all pairs | Ratio or empty |
| `consistent_negative_count` | Paired traces with treatment minus reference below zero | Count from 0 to 67 |
| `consistent_positive_count` | Paired traces with treatment minus reference above zero | Count from 0 to 67 |
| `zero_difference_count` | Paired traces with exactly equal outcomes | Count from 0 to 67 |
| `efficiency_interpretation_authorized` | Whether the prespecified freshness gate permits interpretation of the efficiency contrast | Boolean |

## Outcomes

| Outcome | Definition | Unit |
|---|---|---|
| `freshness_violation_proportion` | Requests whose complete served content violates the workload-specific semantic oracle, divided by requests in the trace | Proportion |
| `mean_request_wall_ns` | Mean request-path wall time within the trace | Nanoseconds per request |
| `operation_thread_cpu_ns` | Total operation-thread CPU consumed during the trace | Nanoseconds per trace |
| `total_origin_response_body_bytes` | Request-path plus publisher origin-response body bytes | Bytes per trace |
| `redis_delivery_payload_bytes` | Delivered notification payload bytes | Bytes per trace |

## Contrast-summary table

`primary_contrast_summary.csv` groups the primary-estimate rows by contrast and
outcome. It records the number of strata, the range of point estimates, counts
of intervals below zero, above zero or including zero, and the range of paired
mean ratios when defined.

## Missing values

There are no missing primary estimates. `paired_mean_ratio` is empty when a
ratio is not defined for every pair, including comparisons whose reference
outcome can be zero.
