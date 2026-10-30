# Training campaign design

Date: 2026-10-29

The training campaign is source-bound by
`experiments/freshness/training_campaign_v1.json`. It uses all ten training seeds
for each of the three workloads and three request/update regimes. One independent
unit is one complete policy-candidate execution over one trace. Requests within a
trace are repeated measurements and are not counted as independent samples.

Cost calibration uses the no-fault Pub/Sub identity and runs all eight policy
families in each matched block. Median serialized update-notification,
invalidation-notification and origin-miss response bytes are estimated by workload
and regime from always-update, always-invalidate and bypass units, respectively.

Fixed-TTL and stale-while-revalidate candidates use the canonical no-fault Pub/Sub
condition because those policies do not consume notification delivery. Repeating
their identical exogenous trace under additional delivery-fault labels would not
create independent information. Event-repair and write-reactive candidates use
both Redis modes under no fault, 100 ms delay, 10% loss and combined stress. These
conditions represent the no-fault reference, maximum declared delay and loss, and
the prespecified combined condition. Other frozen fault levels remain available for
validation and held-out evaluation rather than parameter fitting.

Every candidate block includes matched controls so that every hosted allocation
contains all eight policy families. Candidate selection remains lexicographic at
the full-trace level: minimize mean freshness violations, retain candidates within
one percentage point of the minimum, then minimize mean origin response bytes and
finally use declared candidate order. The planned training execution contains
18,000 full trace units: 720 cost-calibration units, 4,320 time-candidate and
control units, and 12,960 event-candidate and control units.

No value from this campaign is a confirmatory result. Validation may confirm a
locked choice without refitting. Final-test collection remains prohibited until
the policy parameters and precision-based sample size are locked.
