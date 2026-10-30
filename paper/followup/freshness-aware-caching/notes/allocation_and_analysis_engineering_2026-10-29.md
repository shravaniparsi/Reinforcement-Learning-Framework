# Allocation and analysis engineering record

The hosted allocation contract is `experiments/freshness/allocation_design_v1.json`. One allocation block is identified by stage, workload, regime, trace seed, transport and fault profile. The block runs all eight policies in a SHA-256-derived permutation that does not use trace contents. Every policy starts in a new process after complete origin, cache, transport and policy reset. This preserves matched comparisons within an allocation while varying policy order across blocks.

The hosted runtime is Ubuntu 24.04 with Python 3.9.25 and Redis package `5:7.0.15-1ubuntu0.24.04.5`, the package used in all three successful calibration replicates. No application or oracle failure is retried. A declared infrastructure failure permits one replacement allocation, and both attempts remain archived. At most three allocation blocks run concurrently.

The synthetic analysis fixture exercises the frozen code without application study observations. It selects `ttl-50` under the lexicographic fixture, constructs five deterministic 99% paired bootstrap intervals and calculates precision requirements. The fixture's largest calculated requirement is 78 traces, so it correctly exercises the rule that expands the reserved final-test pool before collection. The value 78 is a synthetic branch-coverage result and is not the planned study sample size.

The source-bound artifact is `data/engineering/freshness-analysis-engineering-v1/results.json`. It is labeled `synthetic-analysis-engineering-only` and states that it contains no application study observations.
