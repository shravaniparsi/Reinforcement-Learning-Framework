# Decision log

## 2026-10-29: Separate follow-up evidence

The new paper will not reanalyse the existing cache pilot as its primary dataset. New observations, source locks and analysis plans are required.

## 2026-10-29: Strong-rule-first comparison

The mandatory policies are bypass, tuned fixed TTL and event-driven invalidation. Polling or stale-while-revalidate may be added if supported by the selected applications. A learned policy is conditional on a mechanism gate and must receive no information unavailable to its baselines.

Superseded later on 2026-10-29 by the direct-competitor review and protocol v0.2. Conditional validation and stale-while-revalidate are now mandatory, the Mao et al. rule is a direct comparator, and learning is deferred to a separate future protocol.

## 2026-10-29: No arbitrary scalar reward

Freshness violations, readiness and origin work will be reported separately. The primary decision rule will use a declared freshness constraint before comparing performance/resource outcomes. Any scalar utility would require an externally justified preference model fixed before collection.

## 2026-10-29: Sequence-level experimental units

Because policy actions change later cache state, requests within a trace are dependent. Analysis and uncertainty must use trace/allocation-level units and preserve the full sequence.

## 2026-10-29: Novelty narrowed after direct-competitor review

Mao et al. (HotNets 2024) already propose an adaptive write-reactive update-or-invalidate policy. Cao and Liu establish the classical TTL, polling and invalidation comparison, and Ji et al. propose transparent database-assisted invalidation. The project will not claim generic adaptive-cache or invalidation novelty.

The active contribution is an end-to-end, multi-application evaluation under prompt, delayed, lost and reordered notifications with an independent browser-visible content oracle. The Mao et al. rule becomes a mandatory comparator where applicable.

## 2026-10-29: Learning deferred

No learned policy is part of protocol v0.2. Adding one after observing confirmatory results would create an unfrozen comparison. A separate learning study requires a new protocol and a residual decision mechanism established by this study.

## 2026-10-29: Workload set selected provisionally

The set is a mutable product service, SvelteKit RealWorld at `df796708040f5200ec572b28ab7f88ecee5794dd`, and the React-admin e-commerce demo at `0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a`. The external applications are MIT licensed and independently maintained. Each remains subject to build, oracle and semantic-equivalence gates.

## 2026-10-29: Redis transport modes

Redis Pub/Sub represents at-most-once fire-and-forget delivery. Redis Streams represents persisted, acknowledged delivery with recovery of pending entries. Controlled faults are applied by a recorded study adapter and will not be described as native Redis behavior.
