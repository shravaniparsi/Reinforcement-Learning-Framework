# Imperfect-invalidation cache protocol v0.4 draft

Status: design draft; not authorized for study collection.

This working draft records decisions made after the v0.3 engineering gates. It does not supersede v0.3 and is not authorized for study collection until every item in Section 13 is frozen.

## 1. Objective and contribution

This study evaluates how established application-data cache policies behave when invalidation delivery is prompt, delayed, lost or reordered. It measures browser-visible freshness, response readiness, origin work and control traffic across independently implemented mutable web applications.

The scientific contribution is a prospective end-to-end empirical evaluation with an independent content oracle and controlled notification faults. It is not a claim of a new invalidation algorithm. Rendering strategy remains fixed within each workload.

All observations reported in the Software: Practice and Experience submission, including the 60-request live-cache pilot, are excluded from fitting, selection, estimation and hypothesis tests in this study.

## 2. Research questions

**RQ1.** Under reliable notification delivery, how do bypass, conditional validation, fixed TTL, stale-while-revalidate, always invalidate, always update and a write-reactive update-or-invalidate rule differ in freshness compliance, response readiness, origin work and control traffic?

**RQ2.** How do notification delay, loss and reordering change stale-response frequency, duration and revision lag for event-driven policies, and how effective are bounded repair mechanisms?

**RQ3.** Which policy tradeoffs transport across independently implemented workloads, held-out request/update traces and fresh hosted allocations?

**Exploratory RQ4.** Which observable workload properties, including read/write ratio, object size and update-delivery quality, explain policy rank changes?

No learned policy is part of the core study. A later learning study would require a separate prospective protocol after this study establishes a residual sequential decision problem.

## 3. Working expectations

- Under prompt, reliable delivery, explicit invalidation or update should preserve freshness with fewer origin reads than bypass.
- Conditional validation should preserve freshness while paying an origin round trip or validation cost.
- Fixed TTL and stale-while-revalidate should expose a freshness versus latency and origin-work boundary as update intensity rises.
- Notification loss can create unbounded stale residence unless the policy includes a repair mechanism.
- Delayed or reordered notifications can change whether updating or invalidating is preferable and can expose unsafe implementations.
- No policy is expected to dominate across every freshness rule and workload regime.

## 4. Selected workload set

The provisional confirmatory set contains three independently implemented applications or services:

1. **Mutable product service:** a new study implementation derived from the repository's catalog software, with per-product price, availability and descriptive revisions. No pilot observations are reused.
2. **SvelteKit RealWorld feed:** the MIT-licensed `sveltejs/realworld` application pinned at commit `df796708040f5200ec572b28ab7f88ecee5794dd`, adapted to a controlled mutable article backend. Feed membership, ordering, tags and displayed fields form the semantic response.
3. **React-admin dashboard:** the MIT-licensed `marmelab/react-admin` e-commerce demo pinned at commit `0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a`, adapted from browser-simulated FakeRest data to a controlled mutable backend. The dashboard joins orders, revenue, pending reviews and customers.

The two external user interfaces are independently maintained. Every adaptation will be recorded as a patch against its pinned commit. Each workload must provide:

- a mutable origin with monotonic revision identity;
- a complete response-content oracle;
- a browser-visible or API response whose semantic freshness can be declared;
- equivalent policy integration points;
- deterministic reset and seeding;
- a redistributable license for code, adaptations and traces; and
- enough origin work for cache effects to be measurable without artificial delays.

The W2 and W3 adaptation patches, clean builds and browser semantic gates are complete. A workload leaves the set if its pinned source cannot build reproducibly, its complete oracle cannot be implemented, or its adaptation changes the displayed semantics differently across policies.

## 5. Trace, transport and fault contract

Every matched policy receives the same exogenous trace. A trace contains:

- request time, key/query and client class;
- origin update time, affected data and new revision;
- notification creation time and identity;
- notification delivery time, duplication, loss or reordering outcome; and
- load and network conditions fixed before execution.

Policy execution time must not change future exogenous events. Training, engineering and final-test trace identities remain separate.

The core study uses prospectively generated bounded synthetic traces. Public cache traces do not contain the complete application-query content, revision identity and browser-visible semantic state required by the W1-W3 oracle. The study therefore estimates policy behavior under declared regimes rather than production prevalence. Every trace contains exactly 100 updates. Read-heavy, balanced and write-intensive traces contain 500, 200 and 100 requests, respectively. Inter-event gaps range from 5 to 15 logical milliseconds. The machine-readable design fixes disjoint seed pools for engineering, training, validation, variance planning and final testing. The final-test pool contains 20 available seeds, but the precision rule determines how many are used.

Redis is the selected notification substrate, with two declared modes:

- **Redis Pub/Sub:** a fire-and-forget, at-most-once mode. Redis documents that a notification is permanently lost when a subscriber cannot receive it.
- **Redis Streams:** a persisted mode with explicit acknowledgment, pending-entry inspection and redelivery. One stream and one logical consumer process each workload's updates in source order; multi-consumer reordering is outside the primary configuration.

A study-controlled delivery adapter sits between the committed update and the policy consumer. It applies a machine-readable schedule of delay, loss, duplication and reordered delivery. The adapter records dropped notifications rather than removing them from the evidence. It is part of the experimental treatment and is not presented as native Redis behavior.

The no-fault reference uses the transport without injected faults. A local engineering calibration retained 1,000 messages per mode after 100 warm-up messages. Three sequential GitHub-hosted replicates then retained 5,000 messages per mode after 200 warm-up messages. Hosted Pub/Sub p99 ranged from 0.090832 to 0.157139 ms, and Streams p99 ranged from 0.098138 to 0.155089 ms. Every local and hosted delivery completed within 1 ms. Because the delivery adapter uses an integer-millisecond logical clock, the injected-delay grid is fixed at 0, 1, 10 and 100 ms. Zero means no injected delay. One millisecond is the smallest supported nonzero treatment and exceeds the observed hosted maxima. Ten and 100 ms are logarithmically separated stress levels.

With 100 updates per trace, loss profiles drop exactly 1, 5 or 10 notifications. Duplication profiles duplicate exactly 1 or 5 notifications. Reordering profiles reverse exactly 1 or 5 non-overlapping adjacent update pairs. A combined stress profile applies 10 ms base delay with 5 losses, 5 duplicates and 5 reordered pairs. The single-factor profiles identify each mechanism; the combined profile is the only prespecified interaction condition. Dropped notifications cannot also be duplicated. Matched policies receive the same exogenous trace and fault schedule.

## 6. Mandatory policies

1. **Bypass:** fetch current origin state for every request.
2. **Conditional validation:** validate each reusable response using a revision validator equivalent to ETag or Last-Modified semantics.
3. **Fixed TTL:** choose a TTL from a prespecified grid using training traces only.
4. **Stale-while-revalidate:** serve within a declared stale window while revalidating asynchronously, then block or validate after the window.
5. **Always invalidate:** remove or mark the cached entry invalid when a delivered update notification affects it.
6. **Always update:** replace a cached W1 object from the delivered full-object update. For W2 and W3, the publisher constructs a complete replacement for each affected cached query at the commit revision. The message contains the query identity, commit revision, complete response content and content hash. Construction work, serialized bytes and delivery work are charged to this policy. A delayed message retains its commit-revision snapshot and does not read newer origin state at delivery. A replacement whose revision is not newer than the cached revision is ignored.
7. **Write-reactive update-or-invalidate rule:** use exact per-query counters for the observed number of writes between reads. The cost-minimizing action is update when `E[W] * c_u < c_m + c_i` and invalidate otherwise. Mao et al.'s Section 3.2 derivation and explanation support this direction, while the later sentence introducing the `E[W]` approximation prints the action labels in the opposite direction. The implementation follows the cost derivation and will report this choice. Initial `E[W]` and all three cost parameters are selected using training evidence only and frozen before final testing.
8. **Event-driven policy with repair:** pair invalidation or update with a bounded maximum age or periodic validation so that a lost notification cannot leave an entry stale indefinitely.

The publisher knows the set of currently cached query identities when constructing full-query updates. This is a declared cache-aware update baseline. Invalidation messages carry identity and revision metadata, while update messages also carry replacement content. The resulting difference in construction work and transferred bytes is part of the comparison rather than normalized away. Policies receive the same exogenous requests, commits and delivery-fault schedule. All policy decision, validation, message construction, update and repair costs are measured.

## 7. Freshness and measurement contract

HTTP freshness and semantic freshness are distinct. RFC 9111 governs cache response semantics, while the study's application oracle determines whether the served content reflects the required origin state.

For each response, record independently:

- origin revision at request decision and response completion;
- served revision and a hash of the complete declared response content;
- semantic freshness pass/fail under the workload rule;
- revision lag, stale age and continuous stale-residence duration;
- response latency and browser readiness endpoint, where applicable;
- origin reads, validations, cache hits, notification operations, repair operations and transferred bytes;
- origin handler CPU, wall time and queue time;
- policy decision overhead; and
- all request, browser, oracle, transport and instrumentation failures.

The oracle must detect incorrect fields, membership and ordering when those affect workload semantics. A version label alone is insufficient. Waiting time is not CPU, and process-wide CPU remains separate from request-handler CPU.

## 8. Experimental unit, matching and isolation

The experimental unit is one full policy execution over one trace in one isolated allocation or declared local session. Requests within a unit are dependent observations and are not treated as independent replicates.

Before each unit:

- reset origin data, cache, notification transport and policy state;
- verify the initial revision and empty-cache condition;
- bind the run to a common trace and fault-schedule identity;
- randomize policy order independently of trace contents; and
- record allocation, runtime, source, build and instrumentation identities.

The harness must verify that matched policies observe identical exogenous request, update and fault schedules. Fresh allocations are not assumed to be independent physical hosts.

## 9. Development and evidence partitions

- **Engineering:** validate semantics, instrumentation, resets and failure retention. No estimates enter the paper.
- **Training:** choose TTL, stale window, repair interval and parameters required by the write-reactive rule.
- **Validation:** select among prespecified candidates without refitting.
- **Variance planning:** estimate trace-level variability for the precision rule.
- **Final test:** run frozen policies once on held-out traces and, where feasible, a held-out workload.

Final-test outcomes may not change policies, freshness rules, workloads, endpoints, fault schedules or sample size.

The frozen candidate grid uses 10, 25, 50, 100, 250 and 500 ms for fixed TTL, SWR TTL, SWR stale window and repair age. Initial `E[W]` candidates are 0.25, 0.5, 1, 2, 5 and 10. Write-reactive costs use median serialized update, invalidation and origin-miss bytes by workload and regime in training. Training selects candidates lexicographically: first minimize mean trace-level freshness violations, then retain candidates within 1 percentage point of that minimum and choose the one with fewer mean origin response bytes. Validation confirms the locked choice without refitting.

## 10. Outcomes and analysis principles

The primary admissibility outcome is compliance with a workload-specific freshness rule frozen before collection. Latency or origin savings do not compensate for a policy that violates that rule.

Primary trace-level outcomes are:

- semantic freshness violation proportion;
- stale-residence duration and revision lag;
- readiness or response latency;
- origin reads, validations and handler CPU;
- notification, update and repair traffic; and
- failure proportion by type.

Primary policy contrasts will be paired within workload, trace and fault schedule. The analysis must account for repeated requests within traces and variation across workload, trace and allocation. Effects will be reported with uncertainty intervals and absolute units. No weighted scalar combines staleness, latency, CPU and bytes.

The exact estimand, interval method, multiplicity rule and precision-based sample-size criterion remain open. They must be frozen after workloads and trace generators are selected and before confirmatory collection.

The working statistical plan defines the complete trace execution as the independent unit. Requests within a trace are repeated observations. The primary robustness contrasts compare repair with always invalidation at each loss level; primary adaptation contrasts compare write-reactive with always update and always invalidate under no fault. These five contrast types use 99% percentile bootstrap intervals with 10,000 resamples of complete paired trace units. Secondary estimates use 95% intervals and remain descriptive. Final sample size is selected once from paired variance-planning traces to target a 99% interval half-width of 1 percentage point for freshness differences and 10% of the reference mean for primary efficiency outcomes, with a minimum of 8 seeds. The planning formula is `ceil((2.5758293 * s / h)^2)`. A requirement above the reserved 20-seed pool triggers protocol expansion before final testing.

## 11. Failure, repair and stopping rules

- A content-oracle mismatch, missing origin or served revision, schedule divergence, failed reset or unaccounted request failure invalidates the full experimental unit.
- Invalid units and their diagnostics are retained. They are not silently replaced.
- Any source or instrumentation correction requires a new source lock and recollection of affected stages.
- No passing subset is used for the primary estimate.
- An event-driven policy without a bounded repair path cannot be described as robust to notification loss.
- If all strong policies have operationally indistinguishable outcomes under the declared regimes, report that null comparison rather than adding a learned policy after inspection.
- Stop collection if telemetry materially changes application behavior or matched policies do not receive the same exogenous schedule.

## 12. Reproducibility

Archive protocols, workload selection records, source commits, adaptation patches, licenses, dependency locks, trace sources or generators, fault schedules, build receipts, allocation identities, raw successes and failures, analysis code and checksums. A public versioned release and DOI will be created only after secrets and nonredistributable data are removed or documented.

## 13. Decisions required for v0.4 freeze

1. Pin the Redis version and installation identity used locally and in hosted runs.
2. Choose the hosted environment and allocation structure.
3. Exercise the encoded parameter-selection, paired interval and precision calculations on engineering fixtures before freezing v0.4.
