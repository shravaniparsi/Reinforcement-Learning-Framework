# Literature and novelty review

Date: 29 October 2026

Status: design input for protocols v0.2 and v0.3. This is a targeted novelty review, not a systematic review.

## Review question

What can a new application-level cache-freshness study claim after accounting for established HTTP semantics, strong invalidation schemes, adaptive TTLs, transparent invalidation and recent write-reactive cache policies?

## Finding

A broad claim of a novel adaptive freshness policy is not supportable. Prior work already covers adaptive TTLs, polling, invalidation, transparent database-assisted invalidation, search-result staleness prediction, and a recent adaptive choice between updating and invalidating cached objects.

The defensible gap is an empirical one: an end-to-end evaluation of established freshness policies in independently implemented web applications when invalidation delivery is imperfect. The study can connect origin revisions to browser-visible content and measure stale-response duration, readiness, origin work and control traffic under delayed, lost and reordered notifications. The contribution is the evaluation design and evidence, not a new invalidation algorithm.

## Competitor matrix

| Source | Setting and policies | Evidence | What it establishes | Remaining gap relevant to this study | Status |
|---|---|---|---|---|---|
| Mao, Iyer, Shenker and Stoica, *Revisiting Cache Freshness for Emerging Real-Time Applications*, HotNets 2024, DOI [10.1145/3696348.3696858](https://doi.org/10.1145/3696348.3696858) | In-memory cache freshness with a staleness bound; TTL expiration and polling, always update, always invalidate, and an adaptive write-reactive update-or-invalidate rule | Analysis and simulation using synthetic Poisson traffic plus Meta and Twitter traces | Tight freshness can make TTL costly; update versus invalidate depends on read/write behavior and operation costs; lost or reordered control messages remain a reliability concern | Browser-visible application behavior, independent web applications, hosted executions and controlled notification faults are outside its main evaluation | Primary source verified; direct competitor |
| Ji, Zhou, Zhou and Wang, *The Case of Transparent Cache Invalidation in Web Applications*, arXiv:2311.02384 | Application-level query-result caches; database and cache changes provide precise invalidation through predicate and Bloom-filter indexes | Study of 20 open-source applications, survey of more than 50 engineers, and preliminary TPC-C/YCSB evaluation | Developers find invalidation difficult; transparent database-assisted invalidation can improve precision and cache utility relative to coarse invalidation and TTL | Does not provide an end-to-end browser study of notification delay, loss and reordering across multiple web applications | Primary manuscript verified; direct competitor for transparent invalidation claims |
| Cao and Liu, *Maintaining Strong Cache Consistency in the World Wide Web*, IEEE Transactions on Computers 47(4), 1998 | Adaptive TTL, polling every time and server invalidation | Analysis, implementation and trace replay | Strong invalidation can provide consistency with comparable traffic, workload and response time to adaptive TTL; polling incurs additional control and latency costs | Modern application caches, browser-visible content and explicit fault injection are not evaluated | Bibliographic metadata and paper text verified; foundational baseline source |
| Alici et al., *Timestamp-based Result Cache Invalidation for Web Search Engines*, SIGIR 2011, DOI [10.1145/2009916.2010046](https://doi.org/10.1145/2009916.2010046) | Search-result caches; timestamp features predict whether cached query results are stale | Search-engine-specific evaluation | Timestamp information can support low-overhead stale-query prediction | The object model, user-visible endpoint and invalidation mechanism differ from mutable application data | Metadata verified; adjacent domain |
| Sazoglu et al., *Strategies for Setting Time-to-Live Values in Result Caches*, CIKM 2013, DOI [10.1145/2505515.2507886](https://doi.org/10.1145/2505515.2507886) | Search-result caches; time-, frequency- and click-based TTL policies and hybrids | Search-engine result-cache experiments | TTL selection can use workload signals and hybrids can improve stale traffic and redundant computation | It does not address event delivery faults or browser-visible application correctness | Primary PDF and metadata verified; adjacent domain |
| RFC 9111, *HTTP Caching* | Normative HTTP cache freshness, age, validation, invalidation and conditional requests | Internet Standard | Defines fresh and stale responses, revalidation, validators and conditions for serving stale responses | Application-level semantic freshness can be stricter than HTTP response age and requires an independent content oracle | Standard verified; required semantics source |
| RFC 5861, *HTTP Cache-Control Extensions for Stale Content* | `stale-while-revalidate` and `stale-if-error` | Informational RFC | Permits bounded stale serving while asynchronous validation occurs and defines its traffic-dependent behavior | It specifies semantics rather than comparative application evidence | Standard verified; required baseline source |
| Cho, Shin, Jeon and Yoon, *TTL-Based Cache Utility Maximization Using Deep Reinforcement Learning*, GLOBECOM 2021, DOI [10.1109/GLOBECOM46510.2021.9685845](https://doi.org/10.1109/GLOBECOM46510.2021.9685845) | Utility-driven TTL admission and eviction under changing content popularity | Nonstationary content-request experiments | Learning can adapt TTL cache utility under changing popularity | It optimizes cache utility and replacement rather than application-data correctness under origin updates | Metadata and abstract verified; adjacent learning literature |

## Infrastructure sources

- Redis documents Pub/Sub as at-most-once delivery in which a notification is permanently lost if the subscriber cannot receive it. Messages received by an active subscriber are delivered in publication order.
- Redis documents Streams as an append-only persisted structure with explicit acknowledgment, pending entries and consumer recovery. A single stream and consumer can process in order; multiple consumers can complete work out of order.
- The React-admin e-commerce demo is MIT licensed, obtains dashboard data through a data provider and currently simulates its API in the browser with FakeRest. Its pinned dashboard aggregates orders into revenue, order counts and pending-order lists, with separate review and customer panels.

These are implementation facts, not evidence for the paper's outcome claims. Exact source URLs and pinned revisions must appear in the reproducibility manifest.

## Novelty boundary

The manuscript may claim:

1. a prospective, end-to-end comparison across at least three independently implemented mutable web workloads;
2. an independent revision and content oracle that identifies browser-visible stale responses;
3. controlled delay, loss and reordering of update notifications;
4. matched trace-level comparisons of bypass, conditional validation, fixed TTL, stale-while-revalidate, always invalidate, always update and the Mao et al. write-reactive rule;
5. joint reporting of freshness compliance, stale duration, readiness, origin work and control traffic without an arbitrary weighted score; and
6. transport checks across fresh hosted allocations.

The manuscript must not claim:

- the first adaptive cache-freshness policy;
- the first event-driven or transparent invalidation mechanism;
- that TTL, polling or invalidation are new comparisons;
- that reinforcement learning is necessary without a separate mechanism and evidence;
- production representativeness from synthetic traces alone; or
- exact consistency when the policy can lose update information without repair.

## Design consequences

- The core robustness variable is invalidation delivery quality, not whether a policy is learned.
- Conditional validation and stale-while-revalidate are mandatory HTTP baselines.
- The Mao et al. always-update, always-invalidate and adaptive update-or-invalidate policies are mandatory direct comparators where the workload supports pushed updates.
- A repair mechanism after notification loss must be explicit. Candidate mechanisms include periodic validation or a bounded maximum age.
- Freshness is semantic. The oracle must compare the served response with the origin revision and declared response content, not rely only on HTTP `Age` or a cache-hit label.
- Any learning-based policy is deferred. It can enter a later study only if strong rules leave a measurable decision problem under equal information.

## Resolution update, 31 October 2026

The protocol now uses bounded synthetic traces and explicitly limits its claims
to the declared regimes. Semantic freshness is defined by workload-specific
complete-content oracles. Redis delivery faults are controlled treatments rather
than estimates of native failure rates. Ji et al. remains an arXiv/CoRR preprint
with no verified final venue.

The Mao et al. source contains an internal action-label inconsistency. Its cost
derivation and explanation imply updating when the expected update cost is less
than invalidation plus the subsequent miss, while one evaluation sentence prints
the action labels in the opposite direction. The study implements the
cost-minimizing direction and the manuscript now discloses this interpretation.
The full claim-by-source record is in
`notes/claim_source_audit_2026-10-31.md`.
