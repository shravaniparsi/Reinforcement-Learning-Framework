# Paper handoff

## 2026-10-29 training cost calibration

Phase 1 training cost calibration completed in GitHub Actions run `40982405656`:
90/90 matched blocks and 720/720 full trace units passed. The compact cost lock is
`data/training/freshness-costs-40982405656/locked_costs.json`; interpretation and
counts are recorded in `notes/training_cost_lock_2026-10-29.md`. These are training
inputs only. Candidate fitting, validation, variance planning and final-test
collection remain incomplete.

## 2026-10-29 time-candidate fitting

Fixed-TTL and stale-while-revalidate fitting completed in GitHub Actions run
`40984591923`: 90/90 blocks and 4,320/4,320 full trace units passed. The parameter
lock is
`data/training/freshness-time-candidates-40984591923/selected_time_parameters.json`;
the human-readable record is `notes/time_candidate_lock_2026-10-29.md`. These are
training choices only. Event-policy fitting and every later evidence partition
remain incomplete.

## 2026-10-30 event-candidate fitting

Event-repair and write-reactive fitting completed in GitHub Actions run
`41006126071`: 720/720 blocks and 12,960/12,960 full trace units passed. The
parameter lock is
`data/training/freshness-event-candidates-41006126071-archives/selected_event_parameters.json`;
the archive inventory and 720 compressed raw artifacts are retained in the same
directory. The human-readable record is
`notes/event_candidate_lock_2026-10-30.md`. These are training choices only.
Validation, variance planning and final testing have not begun.

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
- Commit-revision query-complete update construction is implemented for W2 and W3. Engineering tests verify delayed refresh, resource-query replacement, publisher origin-read and byte accounting, and suppression of an older update delivered after a newer revision. Write-reactive actions and write-history increments are fixed at publication, including when delivery is lost.
- Source-bound W1, W2 and W3 semantic replays now cover all eight policies. The W2 and W3 schedules exercise delay, duplication, reordering and loss. Results and their non-inferential interpretation are recorded in `notes/semantic_policy_replays_2026-10-29.md`; the three artifacts explicitly contain no performance observations.
- Bounded synthetic trace design v1 is machine-readable and tested. Each trace has 100 updates; read-heavy, balanced and write-intensive regimes have 500, 200 and 100 requests. Exact fault profiles cover delay, 1/5/10% loss, 1/5% duplication, 1/5% adjacent-pair reordering and one combined stress condition. Evidence-partition seed ranges are disjoint. The decision and scope boundary are in `notes/trace_design_decision_2026-10-29.md`.
- Policy parameter grid v1 freezes 10/25/50/100/250/500 ms candidates for TTL, SWR and repair and six initial `E[W]` candidates. Write-reactive costs are observed serialized bytes rather than subjective weights. The statistical plan defines the full trace execution as `n`, prespecifies the primary contrasts and sets a variance-planning precision rule. See `notes/statistical_analysis_plan_v0.1.md`.
- Statistical calculations are encoded and tested: lexicographic candidate selection, exact paired-unit matching, deterministic 10,000-resample trace bootstrap intervals, 99% primary intervals for five contrast types, and precision-based `n` with protocol expansion when more than 20 final seeds are required.
- Hosted allocation design v1 places all eight randomized policies for a matched trace block on one fresh Ubuntu 24.04 runner, starts a new process and full reset per policy, pins Python 3.9.25 and Redis package `5:7.0.15-1ubuntu0.24.04.5`, forbids application-failure retries and retains both attempts for the single allowed infrastructure retry.
- The source-bound synthetic analysis fixture exercises selection, five primary intervals and pool expansion without study observations. Its intentionally high-variance branch requires 78 traces, which is an engineering branch-coverage result rather than a study sample size. See `notes/allocation_and_analysis_engineering_2026-10-29.md`.
- Protocol v0.4 is frozen at `protocol/protocol_v0.4.md`. It authorizes engineering preflight only. Training, validation and variance planning require a passing hosted preflight; final testing remains locked until earlier stages freeze parameters and `n`.
- All training inputs and parameters are now locked: serialized-byte costs, fixed-TTL and stale-while-revalidate timing, event-repair age and write-reactive initial expected writes. The event campaign completed 720 blocks and 12,960 full-trace units; its 27,360 source files are checksum-bound in the parameter lock.
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

Implement and run the held-out validation partition with every training parameter
fixed and no refitting. If validation passes the prespecified confirmation rule,
run the variance-planning partition and freeze the final sample size. Final-test
collection remains prohibited until both steps complete.
