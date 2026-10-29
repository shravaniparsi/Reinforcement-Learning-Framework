# Freshness-aware caching protocol v0.1

Status: design draft; not authorized for study collection.

## 1. Objective and scope

This study compares cache invalidation policies for mutable web-application data. It measures whether lower response time or lower origin work is obtained by serving stale content, and whether policies with realistic update information can preserve freshness with less origin work than bypass.

Rendering strategy is held fixed within a workload unless a later protocol version declares a separate factorial treatment. The paper is about application data caching, not SSR/CSR selection, framework incremental regeneration or browser asset caching.

The existing live-cache pilot and all observations reported in the Software: Practice and Experience submission are excluded from the new study's fitting, selection and final estimates.

## 2. Research questions

**RQ1.** How do bypass, fixed-TTL and update-aware invalidation policies affect the frequency, duration and severity of stale responses across declared request/update regimes?

**RQ2.** Among policies satisfying the predeclared freshness rule, how do readiness, origin reads, origin CPU, transferred bytes and queueing differ?

**RQ3.** How stable are policy tradeoffs across independently implemented workloads, held-out traces and fresh hosted allocations?

**Exploratory RQ4.** If update information is delayed, incomplete or costly, does an adaptive policy improve on tuned TTL, polling and event-driven engineering rules under the same information and tuning budgets?

RQ4 is disabled unless the mechanism gate in Section 10 passes.

## 3. Working expectations

These expectations guide design checks and do not substitute for the final analysis plan.

- Fixed TTL should reduce origin reads relative to bypass, while its stale-response rate should increase with update intensity or longer TTLs.
- Event-driven invalidation should approach bypass freshness with fewer origin reads when notifications are prompt and reliable.
- Notification delay or loss should expose a measurable freshness/resource boundary rather than a universally best policy.
- A learned policy is not expected to be useful when an explicit rule receives the same reliable update signal.

## 4. Workloads and traces

The final design requires at least three independently implemented application or service workloads. Candidate classes are a mutable catalog, an article/feed listing and an API-backed record view. At least one workload must be derived from an independently maintained open-source application. Exact repositories, commits, licenses, adaptations and semantic oracles remain to be selected.

Each policy receives the same exogenous trace containing:

- request time and requested object/query;
- origin update time, object and new revision;
- notification delivery time or declared notification loss;
- any client/profile or load condition fixed before the trace begins.

Trace parameters and regimes must be justified by public traces, target-system measurements or a narrowly stated synthetic design. Low, medium, bursty and high-change labels may not be assigned until their numerical definitions are fixed. Policy completion times must not change future exogenous event times.

## 5. Mandatory policies

1. **Bypass:** read current origin state for every request.
2. **Fixed TTL:** a prespecified candidate grid tuned only on training traces.
3. **Event-driven invalidation:** invalidate or refresh after the declared notification is observed.
4. **Strong additional rule:** polling or stale-while-revalidate if it matches the selected workloads and exposes its information/cost assumptions.

Optional adaptive predictors or sequential learners must use observable features available at decision time. Baselines must receive the same update/request information. Training, tuning and inference costs are recorded.

## 6. Measurement contract

For every response, independently record:

- origin revision at decision and response completion;
- served revision and content hash;
- freshness-rule pass/fail;
- revision lag and stale duration;
- navigation/request readiness and response latency;
- origin reads, cache hits, notification/poll operations and transferred bytes;
- origin handler CPU, wall time and queue time;
- policy decision overhead;
- all request, browser, oracle and instrumentation failures.

The content oracle must verify the complete declared response, not only a version label. Waiting delay is not reported as CPU. Process-wide CPU and request-thread CPU remain distinct.

## 7. Experimental units and isolation

The experimental unit is one complete policy execution over one trace in an isolated hosted allocation or declared local session. Individual requests are repeated dependent observations.

Before every unit:

- reset origin data, cache, notification/polling state and policy state;
- verify the initial revision and empty-cache condition;
- use a common trace identity shared across matched policies;
- randomize policy execution order independently of trace contents;
- retain allocation, runtime, source, build and trace identities.

Fresh allocations are not assumed to be independent physical hosts. Infrastructure dependence must remain visible in interpretation.

## 8. Data partitions and policy freezing

Workload/trace identities must be partitioned before fitting:

- training: fit candidate TTLs and any adaptive policy;
- validation: select hyperparameters without refitting;
- variance/planning: estimate unit-level variability for the fixed precision rule;
- final test: evaluate frozen policies once on held-out traces and, where feasible, a held-out application.

Browser requests from matched policies may reuse the same exogenous trace but never each other's cache or policy state. Final-test outcomes may not change the policies, freshness rule, endpoints or sample size.

## 9. Outcomes and analysis

The primary admissibility outcome is compliance with a workload-specific freshness rule fixed before collection. Candidate policies that violate the rule are not declared better because they reduce latency or origin work.

Primary reports:

- trace/allocation-level freshness violation rate;
- stale duration and revision lag;
- readiness/latency among all responses and among freshness-compliant responses;
- origin reads and CPU per trace;
- notification/polling traffic and policy overhead.

The final statistical model must respect repeated requests within traces and crossed variation from application, trace and allocation. Paired policy contrasts use matched exogenous traces. The estimand, interval procedure, multiplicity treatment and sample-size/precision rule remain open for protocol v0.2 and require review before collection.

No arbitrary weighted sum of latency, CPU, bytes and staleness is used. Pareto plots or constrained comparisons may display tradeoffs without declaring a universal optimum.

## 10. Mechanism gate for learned policies

An adaptive or reinforcement-learning policy enters the confirmatory comparison only if all conditions hold:

1. actions measurably affect later cache state or costs;
2. update information is delayed, incomplete or costly in a way grounded in the selected workloads;
3. no explicit baseline receives less information than the learned policy;
4. training and feedback budgets are declared and comparable;
5. the learned policy can be frozen before final testing;
6. engineering evidence shows the decision overhead is measurable and safe.

If a strong rule matches the adaptive policy during development, the learned-policy claim is dropped. The engineering comparison remains the study.

## 11. Failure and stopping rules

- Any content-oracle mismatch, missing origin/served revision, unaccounted request failure or trace divergence invalidates the complete experimental unit.
- Invalid units are retained and reported; they are not replaced silently.
- A documented engineering correction requires a new source lock and recollection of every affected stage.
- Collection stops if policy runs do not receive the same exogenous trace, state reset fails or telemetry changes application behavior materially.
- No passing subset is used for the primary estimate.

## 12. Reproducibility

Archive protocols, schedules, trace sources/generators, source commits, adaptation patches, licenses, dependency locks, build receipts, runtime identities, raw successes and failures, analysis code and checksums. Create a versioned release and DOI only after private/local data have been removed or documented.

## 13. Open design decisions for v0.2

- Select and license the three workloads.
- Complete the novelty review and competitor matrix.
- Fix freshness rules and trace regimes.
- Decide whether polling and stale-while-revalidate are mandatory.
- Define notification delay/loss from evidence.
- Choose the hosted environment and allocation structure.
- Freeze the estimand, hierarchical analysis and precision-based sample rule.
- Decide whether the learned-policy mechanism gate passes.
