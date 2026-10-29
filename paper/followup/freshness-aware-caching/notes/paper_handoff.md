# Paper handoff

## Ready

- Distinct contribution and non-overlap boundary.
- Working research questions and mandatory baselines.
- Draft measurement contract and sequence-level experimental unit.
- Manuscript skeleton.
- Targeted novelty review and direct-competitor matrix.
- Protocol v0.3 centered on imperfect invalidation delivery.
- Three pinned provisional workloads and semantic freshness rules.
- Redis Pub/Sub and Streams transport decision.
- Validated schedule, fault-materialization and workload-oracle contracts.
- Deterministic SQLite W1 semantic adapter with historical product snapshots and conditional validators.
- Deterministic SQLite W2 feed adapter and controller-protected RealWorld-compatible origin API.
- Separate W2 Svelte adaptation patch that preserves the earlier rendering-study files and observations.
- Clean pinned W2 production build with frozen dependencies.
- W2 SSR and hydrated-browser content verified against the origin after update, tag change, create and delete operations. The engineering artifact explicitly contains no performance observations.
- Pinned W3 React-admin demo sparse checkout and standalone production build. The retained engineering adaptation adds a frozen pnpm lock, uses the flat dependency layout expected by the upstream Vite configuration and removes one obsolete TypeScript suppression.
- Deterministic W3 multi-entity workload with historical order, review and customer snapshots, strict list-query parsing, conditional validators and a complete single-revision dashboard oracle.
- W3 controlled REST service and versioned upstream adaptation patch.
- W3 browser-visible revenue, counts, lists and referenced customers verified against one-revision oracles across five states. The canonical v4 artifact binds the result to source, build, lock, adaptation-patch and license hashes and contains no performance observations; earlier engineering attempts are retained.
- Common gateway core with bypass, conditional validation, fixed TTL, stale-while-revalidate, delivered-event invalidation, delivered-event update, a write-reactive update-or-invalidate rule and event invalidation with bounded repair. Engineering tests cover stale intervals, background and blocking validation, lost delivery, direct updates, out-of-order update suppression, adaptive decisions, duplicate notification identity, atomic rejection and reset replay.
- Conservative W2 article-feed and W3 resource-query dependency resolvers. Their current entity-level notification payloads cannot reconstruct every affected filtered, sorted and paginated response, so always-update is presently valid for W1 only.
- A documented ambiguity in Mao et al.: the Section 3.2 derivation says to update when update cost is lower, while the later `E[W]` sentence prints the action labels in the opposite direction. The gateway follows the cost-minimizing derivation, `E[W] * c_u < c_m + c_i` means update, and the final Methods must disclose this choice.
- Canonical semantic-only W1 replay across all eight policies at `data/engineering/freshness-w1-policy-replay-v1/results.json`. All runs share one event-trace identity and one fault identity; delayed delivery and its duplicate remain separately visible. The artifact is labeled pre-freeze and contains no performance observations.
- Local no-fault Redis engineering calibration at `data/engineering/freshness-redis-no-fault-local-v1/results.json`, with 100 warm-up and 1,000 retained messages per mode. On this host, Pub/Sub p50/p95/p99 were 0.044667/0.087083/0.101834 ms and Streams p50/p95/p99 were 0.053000/0.069375/0.084917 ms. These are transport sanity checks, not application results and not sufficient alone to freeze the injected-delay grid.
- Manual GitHub workflow `.github/workflows/freshness-redis-calibration.yml` for three sequential hosted-runner replicates, 5,000 retained messages per mode per replicate, raw timings, Redis version and host manifest.
- GitHub run `40976163674` completed successfully for all three replicates. All 30,000 retained hosted deliveries matched the merged source hash and completed within 1 ms. The reviewed summary is in `notes/redis_calibration_summary_2026-10-29.md`; raw artifacts are under `data/engineering/freshness-redis-github-40976163674/`.
- Protocol v0.4 fixes the injected-delay grid at 0, 1, 10 and 100 ms. Loss, duplication and reordering rates remain open until the update count per trace is fixed.
- Protocol v0.4 working draft at `protocol/protocol_v0.4-draft.md`. It chooses cache-aware, query-complete update messages for W2 and W3, captured at the commit revision. Message construction, serialized bytes and delivery work remain policy costs; delayed updates cannot consult newer origin state at delivery.
- Verified seed bibliography for direct and adjacent work.

## Required before protocol freeze

- Trace-source decision: public production-derived traces where defensible, otherwise prospectively generated traces with explicitly bounded claims.
- Implemented full-content freshness oracle for each workload.
- Notification delay, loss, duplication and reordering grids fixed from engineering evidence and a declared sensitivity design.
- Sample-size/precision planning and hierarchical analysis review.

## Required before collection

- Frozen protocol version and machine-readable schedules.
- Independent oracle for origin revision and served content.
- Isolation/reset checks across policies.
- Source, dependency, build and trace manifests.
- Failure-retention and abort rules exercised in engineering runs.

## Current next step

Implement commit-revision query-complete update construction for W2 and W3. Then select or generate the request/update traces, fix the update count per trace and freeze loss, duplication and adjacent-pair reordering rates. Do not collect study data under versions 0.1 through 0.3 or the current v0.4 draft.
