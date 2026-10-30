# Freshness study engineering contracts

This package implements protocol-level interfaces for the prospective cache-freshness study. It does not collect measurements.

- `schema.py` validates exogenous request/update traces and fault directives and produces a stable SHA-256 schedule identity.
- `fault_schedule.py` materializes delivered, duplicated, reordered and dropped notifications while retaining loss records.
- `trace_runner.py` replays logical-time engineering schedules, commits mutations before notification creation and records event, fault and full-schedule identities separately.
- `trace_design_v1.json` and `trace_generator.py` define bounded prospective traces with disjoint evidence partitions and exact fault counts.
- `redis_calibration.py` measures no-fault local Pub/Sub and Streams delivery with raw per-message timings and a host manifest. Its output is transport engineering evidence, not application study data.
- `workload.py` defines the reset, commit, read and semantic-oracle contract shared by each application.
- `catalog_workload.py` is the deterministic SQLite-backed W1 product adapter with per-product revision history.
- `realworld_workload.py` is the deterministic SQLite-backed W2 article-feed adapter with historical membership, ordering and field snapshots.
- `realworld_service.py` exposes W2 through a loopback RealWorld-compatible origin API and controller-only mutation endpoints.
- `dashboard_workload.py` is the versioned W3 order, review and customer adapter with a complete single-revision dashboard oracle.
- `dashboard_service.py` exposes W3 through the React-admin simple REST contract and controller-only mutation and oracle endpoints.
- `cache_gateway.py` is the policy-independent cache layer. Its engineering policies are bypass, conditional validation, fixed TTL, stale-while-revalidate, delivered-event invalidation, delivered-event update, a write-reactive update-or-invalidate rule and event invalidation with bounded repair.
- `dependencies.py` contains conservative W2 feed and W3 resource-query dependency rules. For update actions, the publisher snapshots complete affected cached-query responses at the commit revision and includes their content and hashes in the notification.
- `realworld_browser_smoke.py` and `dashboard_browser_smoke.py` are semantic browser gates. They do not record latency or other performance observations.

The active design is the working draft `paper/followup/freshness-aware-caching/protocol/protocol_v0.4-draft.md`. Study collection remains disabled until protocol v0.4 is frozen.

The trace runner fixes update-or-invalidate actions at publication time. W2 and W3 full-query update content is read from the origin immediately after the commit and stored in the notification, so delayed delivery cannot consult newer origin state. Publication records retain query-construction reads, response bytes and serialized notification bytes.

The write-reactive implementation minimizes the declared throughput cost. It updates when `E[W] * c_u < c_m + c_i` and invalidates otherwise. Exact write-between-read history changes when the origin write is published, including when delivery is later lost; notification delivery does not count the write again. Mao et al. derive the equivalent update condition in Section 3.2, but the later prose describing the `E[W]` approximation prints the action labels in the opposite direction. The implementation follows the derivation and the accompanying cost explanation; this choice must be stated in the final Methods.

The canonical W1 policy replay is a semantic engineering check only:

```sh
python3 -m experiments.freshness.run_gateway_engineering \
  experiments/freshness/schedules/w1_policy_replay_v1.json \
  data/engineering/freshness-w1-policy-replay-v2/results.json
```

The source-bound cross-workload replays use:

- `schedules/w1_policy_replay_v1.json` with `data/engineering/freshness-w1-policy-replay-v2/results.json`;
- `schedules/w2_policy_replay_v1.json` with `data/engineering/freshness-w2-policy-replay-v1/results.json`; and
- `schedules/w3_policy_replay_v1.json` with `data/engineering/freshness-w3-policy-replay-v1/results.json`.

Each artifact records the gateway, runner and schedule hashes and is labeled as semantic engineering evidence without performance observations.

Generate one declared schedule with, for example:

```sh
python3 -m experiments.freshness.trace_generator /tmp/w2-training.json \
  --workload svelte-realworld-feed-v1 \
  --regime read-heavy \
  --partition training \
  --seed 100 \
  --fault-profile loss-1pct \
  --transport redis-pubsub
```

Run the local no-fault Redis calibration with:

```sh
python3 -m experiments.freshness.redis_calibration \
  data/engineering/freshness-redis-no-fault-local-v1/results.json \
  --warmup 100 \
  --samples 1000
```

`.github/workflows/freshness-redis-calibration.yml` repeats the same calibrated operation on three sequential GitHub-hosted allocations. Redis package versions and host details are captured in each result rather than assumed.

Run the pure contract, workload and gateway tests with:

```sh
python3 -m unittest \
  tests.test_freshness_contracts \
  tests.test_freshness_catalog_workload \
  tests.test_freshness_realworld_workload \
  tests.test_freshness_dashboard_workload \
  tests.test_freshness_cache_gateway \
  tests.test_freshness_trace_runner \
  tests.test_freshness_trace_generator
```
