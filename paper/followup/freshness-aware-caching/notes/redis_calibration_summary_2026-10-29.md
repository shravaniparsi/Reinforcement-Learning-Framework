# Redis no-fault engineering calibration

Status: engineering evidence only; not application study data.

GitHub Actions run: `40976163674`

Each hosted replicate used 200 warm-up messages followed by 5,000 retained messages for Redis Pub/Sub and 5,000 for Redis Streams. All three jobs passed their contract tests and retained raw per-message timings. The harness source hash matched the merged source in every artifact. Hosted runs used Redis package `5:7.0.15-1ubuntu0.24.04.5` on `ubuntu-24.04` Azure runners.

| Replicate | Mode | p50 (ms) | p95 (ms) | p99 (ms) | Maximum (ms) |
|---:|---|---:|---:|---:|---:|
| 0 | Pub/Sub | 0.104803 | 0.137773 | 0.157139 | 0.889589 |
| 0 | Streams | 0.105283 | 0.133526 | 0.143197 | 0.180303 |
| 1 | Pub/Sub | 0.104384 | 0.133228 | 0.147141 | 0.741232 |
| 1 | Streams | 0.104782 | 0.138167 | 0.155089 | 0.283107 |
| 2 | Pub/Sub | 0.059506 | 0.078874 | 0.090832 | 0.137978 |
| 2 | Streams | 0.055899 | 0.090029 | 0.098138 | 0.157259 |

The earlier local macOS calibration retained 1,000 messages per mode. Its p99 values were 0.101834 ms for Pub/Sub and 0.084917 ms for Streams. Across local and hosted evidence, all observed deliveries completed within 1 ms.

The delivery adapter uses an integer-millisecond logical clock. Protocol v0.4 therefore fixes injected delay at 0, 1, 10 and 100 ms. Zero represents no injected delay. One millisecond is the smallest nonzero treatment and exceeds the observed hosted maxima. Ten and 100 ms provide logarithmically separated stress levels without presenting them as native Redis behavior.

Loss, duplication and adjacent-pair reordering rates remain open. They depend on the number of updates per trace because a nominal rate must produce enough affected notifications for a trace-level outcome without turning individual requests into independent replicates.

Raw artifacts:

- `data/engineering/freshness-redis-no-fault-local-v1/results.json`
- `data/engineering/freshness-redis-github-40976163674/freshness-redis-40976163674-0/results.json`
- `data/engineering/freshness-redis-github-40976163674/freshness-redis-40976163674-1/results.json`
- `data/engineering/freshness-redis-github-40976163674/freshness-redis-40976163674-2/results.json`
