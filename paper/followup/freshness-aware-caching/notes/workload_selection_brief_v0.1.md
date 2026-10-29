# Workload selection brief v0.1

Date: 29 October 2026

Status: provisional engineering recommendation. No study collection is authorized.

## Selection rule

The set must cover different semantic invalidation problems, permit a complete content oracle, expose equivalent cache-policy integration points and remain feasible on a zero-APC, modest-compute project. A workload is excluded if it requires artificial sleep as its main origin cost, lacks deterministic reset, cannot carry monotonic revisions, or cannot be redistributed under a clear license.

## Recommended provisional set

### W1. Mutable product detail and availability service

**Starting asset:** `apps/benchmark` and `experiments/live_backend.py`.

**Required change:** separate the pilot into a new service under the follow-up study, add per-product revisions, stock and price mutations, conditional validators, notification transport, complete response hashes and real database work. The submitted pilot code may be reused as software, but its observations cannot be reused.

**Semantic freshness rule:** for the requested product, the served identifier, price, availability and descriptive fields must equal the latest committed product snapshot visible at the cache decision time. A later update that commits after that decision is recorded separately and does not retroactively invalidate the response.

**Why retained:** a point-object workload makes update versus invalidate costs interpretable and differs from query-result invalidation.

**Main risk:** the current fixture is too small and synthetic. The redesigned origin must have measurable work without inserted delay and must avoid implying production retail traffic.

### W2. Mutable feed query with membership and ordering

**Starting asset:** the pinned MIT-licensed SvelteKit RealWorld application at commit `df796708040f5200ec572b28ab7f88ecee5794dd` in `experiments/external/svelte-realworld`.

**Required change:** create a new, versioned adaptation patch that adds controlled article creation, tag changes and ranking-time changes to the local backend. Preserve the upstream interface and record every adaptation. Do not reuse its earlier read-only timing observations.

**Semantic freshness rule:** for a declared query, the served article identifiers, order, tags and displayed fields must equal the query result over the latest committed origin snapshot visible at cache decision time.

**Why retained:** the UI is independently developed, the license is already retained and the query result can become stale through membership, ordering or field changes.

**Main risk:** the existing local API is a synthetic read-only fixture. The new backend must support mutations and snapshot-consistent query oracles before the workload qualifies.

### W3. React-admin composite e-commerce dashboard

**Starting asset:** the MIT-licensed `marmelab/react-admin` e-commerce demo pinned at commit `0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a`.

**Required change:** extract or reproducibly build the `examples/demo` application, replace its browser-simulated FakeRest source with a controlled mutable backend, and record the adaptation as a versioned patch. Preserve the dashboard's existing aggregation of orders, revenue, pending reviews and customers.

**Semantic freshness rule:** every displayed aggregate, field and list element must match one committed origin snapshot visible at cache decision time. Mixed-revision responses fail the oracle even if each value existed at some time.

**Why retained:** it is independently developed, uses a distinct React/Vite stack and tests dependency and snapshot invalidation that point objects and feed queries do not cover.

**Main risk:** the upstream monorepo is large and the demo currently generates data inside the browser. The workload is excluded if a pinned, minimal build and controlled-backend adaptation cannot be made reproducible without modifying its displayed semantics.

## Rejected shortcuts

- Treating the existing catalog and article pages inside one Next.js fixture as three independent applications.
- Reusing the 60-request cache pilot as a new dataset.
- Using the public RealWorld API or another live service whose state and request traces cannot be reset or audited.
- Adding artificial latency as the main source of policy differences.
- Calling HTTP `Age` alone a semantic freshness oracle.

## Common cache and transport interface

Each workload should implement the same policy-facing operations while retaining its own application logic:

- `read(key_or_query, validator)` returns content, revision, validators, bytes and origin timing;
- `commit(mutation)` returns the committed revision and affected dependency set;
- `notify(revision, affected_set, optional_payload)` enters the controlled delivery layer;
- `snapshot_oracle(key_or_query, decision_revision)` returns the exact expected response;
- `reset(seed)` restores the declared initial state.

The controlled delivery layer records creation, duplication, delay, loss, reorder position and delivery time. Application code must not inspect the planned fault schedule.

## Freeze gates

Before a workload enters the frozen protocol v0.4, verify:

1. license and exact source identity;
2. deterministic reset and mutation replay;
3. full-content oracle, including membership and ordering where applicable;
4. equal policy information and integration points;
5. measurable origin cost without artificial sleep;
6. identical exogenous trace and fault schedule across policies;
7. retained failures and schedule-divergence checks; and
8. no numerical evidence from the submitted article entering the new study.

## Immediate engineering order

1. Extract the common trace, notification and oracle interfaces without collecting measurements.
2. Convert W1 to per-object revisions and conditional validation.
3. Extend the pinned RealWorld adapter for controlled mutations and feed snapshots.
4. Build a minimal pinned React-admin dashboard and replace FakeRest with the controlled backend.
5. Run semantic smoke tests and fault-injection tests before defining timing regimes.
