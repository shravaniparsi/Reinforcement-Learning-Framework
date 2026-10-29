# Freshness study engineering contracts

This package implements protocol-level interfaces for the prospective cache-freshness study. It does not collect measurements.

- `schema.py` validates exogenous request/update traces and fault directives and produces a stable SHA-256 schedule identity.
- `fault_schedule.py` materializes delivered, duplicated, reordered and dropped notifications while retaining loss records.
- `trace_runner.py` replays logical-time engineering schedules, commits mutations before notification creation and records event, fault and full-schedule identities separately.
- `redis_calibration.py` measures no-fault local Pub/Sub and Streams delivery with raw per-message timings and a host manifest. Its output is transport engineering evidence, not application study data.
- `workload.py` defines the reset, commit, read and semantic-oracle contract shared by each application.
- `catalog_workload.py` is the deterministic SQLite-backed W1 product adapter with per-product revision history.
- `realworld_workload.py` is the deterministic SQLite-backed W2 article-feed adapter with historical membership, ordering and field snapshots.
- `realworld_service.py` exposes W2 through a loopback RealWorld-compatible origin API and controller-only mutation endpoints.
- `dashboard_workload.py` is the versioned W3 order, review and customer adapter with a complete single-revision dashboard oracle.
- `dashboard_service.py` exposes W3 through the React-admin simple REST contract and controller-only mutation and oracle endpoints.
- `cache_gateway.py` is the policy-independent cache layer. Its engineering policies are bypass, conditional validation, fixed TTL, stale-while-revalidate, delivered-event invalidation, delivered-event update, a write-reactive update-or-invalidate rule and event invalidation with bounded repair.
- `dependencies.py` contains conservative W2 feed and W3 resource-query dependency rules. The current W2 and W3 notifications identify affected queries but do not contain enough state to update arbitrary filtered, sorted and paginated query responses. Always-update therefore remains a W1-only comparison unless the notification contract is expanded before protocol freeze.
- `realworld_browser_smoke.py` and `dashboard_browser_smoke.py` are semantic browser gates. They do not record latency or other performance observations.

The active design is `paper/followup/freshness-aware-caching/protocol/protocol_v0.3.md`. Study collection remains disabled until protocol v0.4 is frozen.

The write-reactive implementation minimizes the declared throughput cost. It updates when `E[W] * c_u < c_m + c_i` and invalidates otherwise. Mao et al. derive the equivalent update condition in Section 3.2, but the later prose describing the `E[W]` approximation prints the action labels in the opposite direction. The implementation follows the derivation and the accompanying cost explanation; this choice must be stated in the final Methods.

The canonical W1 policy replay is a semantic engineering check only:

```sh
python3 -m experiments.freshness.run_gateway_engineering \
  experiments/freshness/schedules/w1_policy_replay_v1.json \
  data/engineering/freshness-w1-policy-replay-v1/results.json
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
  tests.test_freshness_trace_runner
```
