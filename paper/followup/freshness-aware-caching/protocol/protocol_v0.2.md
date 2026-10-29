# Imperfect-invalidation cache protocol v0.2

Status: design draft; not authorized for study collection.

This version supersedes v0.1 for design work. Version 0.1 remains preserved as the pre-literature design record.

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

## 4. Workload contract

The confirmatory design requires at least three independently implemented applications or services. Candidate semantic classes are:

1. a product or inventory detail endpoint where price or availability changes;
2. an article or feed listing where membership and ordering change; and
3. an API-backed record or dashboard view where several fields change together.

At least one workload must be adapted from an independently maintained open-source application. Each selected workload must provide:

- a mutable origin with monotonic revision identity;
- a complete response-content oracle;
- a browser-visible or API response whose semantic freshness can be declared;
- equivalent policy integration points;
- deterministic reset and seeding;
- a redistributable license for code, adaptations and traces; and
- enough origin work for cache effects to be measurable without artificial delays.

Repository, commit, license, adaptation and exclusion decisions remain open. Workload selection must be recorded before engineering results are compared.

## 5. Trace and fault contract

Every matched policy receives the same exogenous trace. A trace contains:

- request time, key/query and client class;
- origin update time, affected data and new revision;
- notification creation time and identity;
- notification delivery time, duplication, loss or reordering outcome; and
- load and network conditions fixed before execution.

Policy execution time must not change future exogenous events. Training, engineering and final-test trace identities remain separate.

The fault design must include a no-fault reference and declared levels of notification delay, loss and reordering. Numerical levels are not yet frozen. They must come from measurements of the selected transport, documented service behavior or a clearly labeled sensitivity grid. Faults will be generated from a machine-readable schedule and replayed identically across matched policies.

## 6. Mandatory policies

1. **Bypass:** fetch current origin state for every request.
2. **Conditional validation:** validate each reusable response using a revision validator equivalent to ETag or Last-Modified semantics.
3. **Fixed TTL:** choose a TTL from a prespecified grid using training traces only.
4. **Stale-while-revalidate:** serve within a declared stale window while revalidating asynchronously, then block or validate after the window.
5. **Always invalidate:** remove or mark the cached entry invalid when a delivered update notification affects it.
6. **Always update:** replace the cached entry from the delivered update when the cache contains the affected object and the notification carries sufficient state.
7. **Write-reactive update-or-invalidate rule:** reproduce the auditable cost/read-write decision described by Mao et al. using only observable information and parameters frozen before final testing.
8. **Event-driven policy with repair:** pair invalidation or update with a bounded maximum age or periodic validation so that a lost notification cannot leave an entry stale indefinitely.

If a workload cannot support a policy without changing its semantics, record the reason before collection and restrict the cross-workload estimand. Policies must receive equal request and notification information. All policy decision, validation, update and repair costs are measured.

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

## 13. Decisions required for v0.3 freeze

1. Select and license the three workloads.
2. Define semantic freshness for each complete response.
3. Choose the notification transport and justify delay, loss and reordering levels.
4. Select trace sources or freeze a bounded synthetic generator.
5. Reproduce the Mao et al. rule and specify its parameter-estimation budget.
6. Fix TTL, stale-window and repair candidate grids.
7. Choose the hosted environment and allocation structure.
8. Freeze the trace-level estimand, hierarchical analysis and precision rule.
9. Complete an engineering run that exercises schedule matching, reset checks and retained failures.
