# Experiment Results Comparison

## Performance Metrics

| Strategy | Reward | Latency (ms) | TTFB (ms) | TTI (ms) | CPU (s) | Bandwidth (B) | Cache Hit |
|----------|--------|--------------|-----------|----------|---------|---------------|----------|
| RL-Agent | 108.3020 | 23.06 | 10.84 | 25.45 | 0.0101 | 2064 | 0.0000 |
| CSR-Only | 91.5920 | 20.43 | 10.21 | 30.64 | 0.0075 | 1536 | 0.0000 |
| SSR-Only | 32.8819 | 52.59 | 26.29 | 57.85 | 0.0250 | 5120 | 0.0000 |
| SSG-Only | 147.7016 | 7.79 | 2.34 | 7.01 | 0.0025 | 512 | 0.0000 |
| ISR-Only | 135.5712 | 26.22 | 7.86 | 23.59 | 0.0038 | 768 | 0.0000 |
| STREAM-Only | 79.1976 | 22.73 | 11.37 | 25.00 | 0.0100 | 2048 | 0.0000 |
| PARTIAL-Only | 110.0713 | 31.60 | 15.80 | 34.76 | 0.0125 | 2560 | 0.0000 |
| Random | 101.1070 | 23.51 | 11.13 | 26.45 | 0.0102 | 2090 | 0.0000 |
| RoundRobin | 103.4494 | 22.42 | 10.60 | 25.42 | 0.0096 | 1975 | 0.0000 |
| Greedy | 98.1844 | 87.60 | 31.28 | 85.82 | 0.0130 | 2660 | 0.0000 |

## Strategy Distribution (RL-Agent)

| Strategy | Usage |
|----------|-------|
| PARTIAL | 35.3% |
| SSG | 25.2% |
| STREAM | 13.0% |
| CSR | 12.7% |
| SSR | 9.1% |
| ISR | 4.7% |

## Statistical Significance

(To be filled after analysis)
