# Statistical Analysis Report

**Date:** 2026-09-04 17:38:05

**Significance Level (α):** 0.05

## 1. Descriptive Statistics

| Strategy | N | Mean | Std | Min | Max | Median | P25 | P75 |
|----------|---|------|-----|-----|-----|--------|-----|-----|
| RL-Agent | 240 | 108.3020 | 23.9037 | -104.5721 | 139.9256 | 112.5161 | 104.8262 | 119.6027 |
| CSR-Only | 240 | 91.5920 | 38.3605 | -303.1860 | 188.6690 | 100.3888 | 92.9797 | 102.6095 |
| SSR-Only | 240 | 32.8819 | 46.0111 | -261.6377 | 113.5009 | 47.7891 | 22.6261 | 56.6397 |
| SSG-Only | 240 | 147.7016 | 19.8301 | 14.2399 | 338.1257 | 149.1129 | 147.1482 | 150.6964 |
| ISR-Only | 240 | 135.5712 | 36.4357 | -257.5489 | 357.4553 | 139.1865 | 134.1835 | 142.1426 |
| STREAM-Only | 240 | 79.1976 | 33.8198 | -103.7594 | 124.9624 | 89.8668 | 79.9428 | 96.8634 |
| PARTIAL-Only | 240 | 110.0713 | 48.1822 | -410.4838 | 362.5949 | 122.1695 | 107.1649 | 127.1585 |
| Random | 240 | 101.1070 | 45.6506 | -343.6905 | 431.3274 | 108.6284 | 99.7560 | 113.5917 |
| RoundRobin | 240 | 103.4494 | 35.5469 | -162.6848 | 193.4525 | 110.0575 | 100.7196 | 114.3888 |
| Greedy | 240 | 98.1844 | 53.9815 | -632.1725 | 255.0052 | 102.0296 | 98.4421 | 105.7797 |

## 2. Normality Tests (Shapiro-Wilk)

| Strategy | W-statistic | p-value | Normal (α=0.05) |
|----------|-------------|---------|------------------|
| RL-Agent | 0.9708 | 0.2485 | Yes |
| CSR-Only | 0.6099 | 0.0000 | No |
| SSR-Only | 0.7625 | 0.0000 | No |
| SSG-Only | 0.3359 | 0.0000 | No |
| ISR-Only | 0.2337 | 0.0000 | No |
| STREAM-Only | 0.8993 | 0.0005 | No |
| PARTIAL-Only | 0.3227 | 0.0000 | No |
| Random | 0.5244 | 0.0000 | No |
| RoundRobin | 0.7070 | 0.0000 | No |
| Greedy | 0.5090 | 0.0000 | No |

## 3. Overall Comparison (Omnibus Test)

- **Test:** Kruskal-Wallis
- **Statistic:** 1594.1141
- **p-value:** 0.000000
- **Effect Size (η²):** 0.3587 (large)
- **Significant:** Yes
- **Interpretation:** Significant differences exist between strategies

## 4. Pairwise Comparisons (Bonferroni-corrected)

| Comparison | Test | Statistic | p-value | Effect Size | Significant | Interpretation |
|------------|------|-----------|---------|-------------|-------------|----------------|
| RL-Agent vs CSR-Only | Wilcoxon signed-rank | 4136.0000 | 0.000000 | 0.5228 (medium) | Yes | RL-Agent significantly outperforms CSR-Only |
| RL-Agent vs SSR-Only | Wilcoxon signed-rank | 230.0000 | 0.000000 | 2.0571 (large) | Yes | RL-Agent significantly outperforms SSR-Only |
| RL-Agent vs SSG-Only | Wilcoxon signed-rank | 656.0000 | 0.000000 | -1.7940 (large) | Yes | SSG-Only significantly outperforms RL-Agent |
| RL-Agent vs ISR-Only | Wilcoxon signed-rank | 1328.0000 | 0.000000 | -0.8850 (large) | Yes | ISR-Only significantly outperforms RL-Agent |
| RL-Agent vs STREAM-Only | Wilcoxon signed-rank | 1341.0000 | 0.000000 | 0.9939 (large) | Yes | RL-Agent significantly outperforms STREAM-Only |
| RL-Agent vs PARTIAL-Only | Wilcoxon signed-rank | 10081.0000 | 0.002141 | -0.0465 (negligible) | Yes | PARTIAL-Only significantly outperforms RL-Agent |
| RL-Agent vs Random | Wilcoxon signed-rank | 9062.0000 | 0.000024 | 0.1975 (negligible) | Yes | RL-Agent significantly outperforms Random |
| RL-Agent vs RoundRobin | Wilcoxon signed-rank | 10828.0000 | 0.033414 | 0.1602 (negligible) | Yes | RL-Agent significantly outperforms RoundRobin |
| RL-Agent vs Greedy | Wilcoxon signed-rank | 6618.0000 | 0.000000 | 0.2424 (small) | Yes | RL-Agent significantly outperforms Greedy |
| CSR-Only vs SSR-Only | Wilcoxon signed-rank | 1133.0000 | 0.000000 | 1.3860 (large) | Yes | CSR-Only significantly outperforms SSR-Only |
| CSR-Only vs SSG-Only | Wilcoxon signed-rank | 312.0000 | 0.000000 | -1.8376 (large) | Yes | SSG-Only significantly outperforms CSR-Only |
| CSR-Only vs ISR-Only | Wilcoxon signed-rank | 1004.0000 | 0.000000 | -1.1756 (large) | Yes | ISR-Only significantly outperforms CSR-Only |
| CSR-Only vs STREAM-Only | Wilcoxon signed-rank | 5147.0000 | 0.000000 | 0.3428 (small) | Yes | CSR-Only significantly outperforms STREAM-Only |
| CSR-Only vs PARTIAL-Only | Wilcoxon signed-rank | 5258.0000 | 0.000000 | -0.4243 (small) | Yes | PARTIAL-Only significantly outperforms CSR-Only |
| CSR-Only vs Random | Wilcoxon signed-rank | 7091.0000 | 0.000000 | -0.2257 (small) | Yes | Random significantly outperforms CSR-Only |
| CSR-Only vs RoundRobin | Wilcoxon signed-rank | 4674.0000 | 0.000000 | -0.3206 (small) | Yes | RoundRobin significantly outperforms CSR-Only |
| CSR-Only vs Greedy | Wilcoxon signed-rank | 7248.0000 | 0.000000 | -0.1408 (negligible) | Yes | Greedy significantly outperforms CSR-Only |
| SSR-Only vs SSG-Only | Wilcoxon signed-rank | 1.0000 | 0.000000 | -3.2410 (large) | Yes | SSG-Only significantly outperforms SSR-Only |
| SSR-Only vs ISR-Only | Wilcoxon signed-rank | 125.0000 | 0.000000 | -2.4744 (large) | Yes | ISR-Only significantly outperforms SSR-Only |
| SSR-Only vs STREAM-Only | Wilcoxon signed-rank | 1991.0000 | 0.000000 | -1.1470 (large) | Yes | STREAM-Only significantly outperforms SSR-Only |
| SSR-Only vs PARTIAL-Only | Wilcoxon signed-rank | 329.0000 | 0.000000 | -1.6385 (large) | Yes | PARTIAL-Only significantly outperforms SSR-Only |
| SSR-Only vs Random | Wilcoxon signed-rank | 673.0000 | 0.000000 | -1.4886 (large) | Yes | Random significantly outperforms SSR-Only |
| SSR-Only vs RoundRobin | Wilcoxon signed-rank | 583.0000 | 0.000000 | -1.7164 (large) | Yes | RoundRobin significantly outperforms SSR-Only |
| SSR-Only vs Greedy | Wilcoxon signed-rank | 820.0000 | 0.000000 | -1.3020 (large) | Yes | Greedy significantly outperforms SSR-Only |
| SSG-Only vs ISR-Only | Wilcoxon signed-rank | 3432.0000 | 0.000000 | 0.4135 (small) | Yes | SSG-Only significantly outperforms ISR-Only |
| SSG-Only vs STREAM-Only | Wilcoxon signed-rank | 6.0000 | 0.000000 | 2.4711 (large) | Yes | SSG-Only significantly outperforms STREAM-Only |
| SSG-Only vs PARTIAL-Only | Wilcoxon signed-rank | 910.0000 | 0.000000 | 1.0214 (large) | Yes | SSG-Only significantly outperforms PARTIAL-Only |
| SSG-Only vs Random | Wilcoxon signed-rank | 1207.0000 | 0.000000 | 1.3239 (large) | Yes | SSG-Only significantly outperforms Random |
| SSG-Only vs RoundRobin | Wilcoxon signed-rank | 802.0000 | 0.000000 | 1.5375 (large) | Yes | SSG-Only significantly outperforms RoundRobin |
| SSG-Only vs Greedy | Wilcoxon signed-rank | 963.0000 | 0.000000 | 1.2177 (large) | Yes | SSG-Only significantly outperforms Greedy |
| ISR-Only vs STREAM-Only | Wilcoxon signed-rank | 444.0000 | 0.000000 | 1.6037 (large) | Yes | ISR-Only significantly outperforms STREAM-Only |
| ISR-Only vs PARTIAL-Only | Wilcoxon signed-rank | 2518.0000 | 0.000000 | 0.5970 (medium) | Yes | ISR-Only significantly outperforms PARTIAL-Only |
| ISR-Only vs Random | Wilcoxon signed-rank | 1485.0000 | 0.000000 | 0.8345 (large) | Yes | ISR-Only significantly outperforms Random |
| ISR-Only vs RoundRobin | Wilcoxon signed-rank | 1498.0000 | 0.000000 | 0.8924 (large) | Yes | ISR-Only significantly outperforms RoundRobin |
| ISR-Only vs Greedy | Wilcoxon signed-rank | 1295.0000 | 0.000000 | 0.8118 (large) | Yes | ISR-Only significantly outperforms Greedy |
| STREAM-Only vs PARTIAL-Only | Wilcoxon signed-rank | 3029.0000 | 0.000000 | -0.7417 (medium) | Yes | PARTIAL-Only significantly outperforms STREAM-Only |
| STREAM-Only vs Random | Wilcoxon signed-rank | 3594.0000 | 0.000000 | -0.5454 (medium) | Yes | Random significantly outperforms STREAM-Only |
| STREAM-Only vs RoundRobin | Wilcoxon signed-rank | 1846.0000 | 0.000000 | -0.6990 (medium) | Yes | RoundRobin significantly outperforms STREAM-Only |
| STREAM-Only vs Greedy | Wilcoxon signed-rank | 2456.0000 | 0.000000 | -0.4215 (small) | Yes | Greedy significantly outperforms STREAM-Only |
| PARTIAL-Only vs Random | Wilcoxon signed-rank | 7637.0000 | 0.000000 | 0.1910 (negligible) | Yes | PARTIAL-Only significantly outperforms Random |
| PARTIAL-Only vs RoundRobin | Wilcoxon signed-rank | 8797.0000 | 0.000006 | 0.1564 (negligible) | Yes | PARTIAL-Only significantly outperforms RoundRobin |
| PARTIAL-Only vs Greedy | Wilcoxon signed-rank | 7170.0000 | 0.000000 | 0.2323 (small) | Yes | PARTIAL-Only significantly outperforms Greedy |
| Random vs RoundRobin | Wilcoxon signed-rank | 12686.0000 | 1.000000 | -0.0573 (negligible) | No | No significant difference between Random and RoundRobin |
| Random vs Greedy | Wilcoxon signed-rank | 10456.0000 | 0.009005 | 0.0585 (negligible) | Yes | Random significantly outperforms Greedy |
| RoundRobin vs Greedy | Wilcoxon signed-rank | 8627.0000 | 0.000003 | 0.1152 (negligible) | Yes | RoundRobin significantly outperforms Greedy |

## 5. 95% Confidence Intervals

| Strategy | Mean | Lower CI | Upper CI |
|----------|------|----------|----------|
| RL-Agent | 108.3020 | 105.2561 | 111.3479 |
| CSR-Only | 91.5920 | 86.7039 | 96.4801 |
| SSR-Only | 32.8819 | 27.0189 | 38.7448 |
| SSG-Only | 147.7016 | 145.1748 | 150.2285 |
| ISR-Only | 135.5712 | 130.9284 | 140.2140 |
| STREAM-Only | 79.1976 | 74.8881 | 83.5070 |
| PARTIAL-Only | 110.0713 | 103.9317 | 116.2109 |
| Random | 101.1070 | 95.2900 | 106.9240 |
| RoundRobin | 103.4494 | 98.9198 | 107.9790 |
| Greedy | 98.1844 | 91.3059 | 105.0630 |

## 6. RL-Agent vs Baselines (Cohen's d)

| Baseline | Cohen's d | Effect Size | Interpretation |
|----------|-----------|-------------|----------------|
| CSR-Only | 0.5228 | medium | RL-Agent significantly outperforms CSR-Only |
| SSR-Only | 2.0571 | large | RL-Agent significantly outperforms SSR-Only |
| SSG-Only | -1.7940 | large | SSG-Only significantly outperforms RL-Agent |
| ISR-Only | -0.8850 | large | ISR-Only significantly outperforms RL-Agent |
| STREAM-Only | 0.9939 | large | RL-Agent significantly outperforms STREAM-Only |
| PARTIAL-Only | -0.0465 | negligible | PARTIAL-Only significantly outperforms RL-Agent |
| Random | 0.1975 | negligible | RL-Agent significantly outperforms Random |
| RoundRobin | 0.1602 | negligible | RL-Agent significantly outperforms RoundRobin |
| Greedy | 0.2424 | small | RL-Agent significantly outperforms Greedy |

## 7. Summary

- **RL-Agent Mean Reward:** 108.3020
- **Best Baseline:** SSG-Only (147.7016)
- **Improvement over Best Baseline:** -26.68%

The RL-Agent does not outperform the best baseline (SSG-Only).
