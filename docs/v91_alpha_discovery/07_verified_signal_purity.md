# Verified Signal Purity Test

## Purpose

Test the historical `D4_htf @ 300/40/h5` claim without TP/SL, position
occupancy, entry lag, trade selection, or exit-engine behavior.

Catalog:

- Range: 2020-05-22 to 2026-05-21
- Volume bars: 509,147
- Threshold: 300 BTC
- Catalog hash: `234617593ff6f697e1a584b88b6f8b1b9ee1bd2a8cc2e0b314bb3e8aca4a7233`
- Lookback: 40 bars
- Forward horizon: 5 bars

Signal success means the close five volume bars after the signal is in the
predicted direction relative to the signal-bar close.

## Result

| Mode | Events | Hit Rate | Mean Signed Return | IC |
|---|---:|---:|---:|---:|
| Divergence without HTF filter | 51,751 | 52.2405% | 1.8375 bps | 0.040900 |
| Legacy D4, full-history HTF quantile | 21,991 | 52.8489% | 2.2906 bps | 0.048956 |
| D4, past-only rolling HTF quantile | 22,016 | 53.1114% | 2.3895 bps | 0.052391 |

The old `53.29%` claim is directionally reproducible on the verified catalog.
The exact value changes because the old diagnostic used a different archive
set and a full-history HTF threshold. The past-only implementation is slightly
better in aggregate, so the historical result is not explained by that
lookahead issue.

## Past-Only Year Breakdown

| Signal Year | Events | Hit Rate | Mean Signed Return | IC |
|---|---:|---:|---:|---:|
| 2020 | 2,289 | 51.5946% | 1.0847 bps | 0.081786 |
| 2021 | 4,874 | 53.6931% | 6.4123 bps | 0.083229 |
| 2022 | 7,540 | 54.0451% | 1.7258 bps | 0.050484 |
| 2023 | 4,678 | 53.8264% | 0.8011 bps | 0.044089 |
| 2024 | 1,380 | 50.0725% | 1.0454 bps | 0.030887 |
| 2025 | 969 | 48.5036% | 0.6152 bps | 0.003512 |
| 2026 partial | 286 | 49.3007% | 0.2486 bps | 0.001780 |

The directional effect is not stable in recent years. Hit rate is effectively
flat in 2024 and below 50% in 2025-2026. Positive mean return with sub-50% hit
rate reflects a small number of larger favorable moves, not consistent
directional accuracy.

## Side Breakdown

| Side | Events | Hit Rate | Mean Signed Return |
|---|---:|---:|---:|
| Long | 8,065 | 54.2715% | 3.1592 bps |
| Short | 13,951 | 52.4407% | 1.9445 bps |

## Decision

The D4 signal contains a real but weak historical directional effect. It does
not justify the historical 80-93% trade win-rate claims, and its average gross
five-bar move of 2.39 bps is below realistic taker round-trip costs.

Retain D4 as a benchmark and research feature. Do not promote it as a direct
strategy. Any future use must demonstrate positive out-of-sample expectancy
after explicit costs, with special attention to the post-2023 decay.

Raw result:
`results/v91_parameter_test/verified_signal_purity_lb40_h5.json`
