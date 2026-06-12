# V9.1 Recovered-Context Diagnostics

Guide concepts were evaluated only as isolated research features. No AI decision, arbitrary score, or live rule was used.

## Method

- D4 uses the verified 300 BTC catalog, 40-bar lookback, and past-only rolling HTF threshold.
- Structure uses the slope of the prior 40 completed volume bars; support/resistance uses prior 100-bar extrema within 0.3%.
- MTF biases use EMA20 on completed 15m, 1h, 4h, and daily buckets.
- Volume profile uses 50 bins over the prior 100 completed bars.
- Exit research enters at the next volume-bar open and applies 12 bps round-trip cost.
- Exit variants are fixed 0.6%/0.3% TP/SL, first adverse CVD bar, 24-bar time exit, fixed-entry profile levels, trailing after 0.5% MFE, and 50% partial at 0.3%.

## Overall D4 Decay

| Period | Events | Hit Rate | Mean SFR | IC | T-stat | Cost-adjusted expectancy |
|---|---:|---:|---:|---:|---:|---:|
| all | 22,015 | 53.11% | 2.390 bps | 0.0524 | 7.57 | -9.610 bps |
| 2020-2023 | 19,381 | 53.61% | 2.605 bps | 0.0585 | 8.01 | -9.395 bps |
| 2024-2026 | 2,634 | 49.43% | 0.808 bps | 0.0178 | 0.72 | -11.192 bps |

## Context Buckets

### Market Structure

| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| uptrend | 1,328 | 53.01% | 3.660 | 0.0353 | 2.35 | 1.231 | 1.979 | 0.15% | 3.658 | 3.670 | -8.340 |
| downtrend | 631 | 54.83% | 5.624 | 0.0000 | 2.70 | 2.050 | 3.173 | 0.13% | 6.315 | 2.961 | -6.376 |
| range | 20,056 | 53.07% | 2.205 | 0.0495 | 6.79 | 0.917 | 1.370 | 0.42% | 2.439 | 0.331 | -9.795 |

### Key Level

| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| near_support | 3,882 | 52.47% | 1.584 | -0.0004 | 2.35 | 0.722 | 1.074 | 0.20% | 1.269 | 4.242 | -10.416 |
| near_resistance | 7,356 | 51.82% | 0.813 | 0.0042 | 1.67 | 0.372 | 0.547 | 0.71% | 1.050 | -1.214 | -11.187 |
| no_key_level | 10,777 | 54.23% | 3.758 | 0.0737 | 7.56 | 1.391 | 2.123 | 0.30% | 4.202 | 0.905 | -8.242 |

### Mtf Alignment

| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aligned_with_d4 | 2,023 | 56.90% | 6.447 | 0.1094 | 4.97 | 2.111 | 3.394 | 0.20% | 6.739 | 0.306 | -5.553 |
| partially_aligned | 2,025 | 54.07% | 0.334 | 0.0136 | 0.39 | 0.164 | 0.218 | 0.24% | -0.263 | 15.661 | -11.666 |
| against_d4 | 6,176 | 50.47% | 0.292 | 0.0131 | 0.52 | 0.126 | 0.183 | 0.35% | 0.452 | -0.588 | -11.708 |
| mixed | 11,791 | 53.69% | 3.147 | 0.0657 | 7.24 | 1.274 | 1.954 | 0.35% | 3.468 | 0.969 | -8.853 |

### Poc Context

| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| above_poc | 9,887 | 52.28% | 2.322 | 0.0235 | 4.48 | 0.860 | 1.295 | 0.51% | 2.546 | 1.046 | -9.678 |
| below_poc | 5,988 | 54.01% | 4.102 | 0.0757 | 5.90 | 1.458 | 2.205 | 0.28% | 4.431 | 2.366 | -7.898 |
| near_poc | 6,140 | 53.58% | 0.831 | 0.0395 | 2.34 | 0.571 | 0.844 | 0.20% | 1.141 | -8.147 | -11.169 |

### Value Context

| Bucket | Events | Hit Rate | Mean SFR | IC | T-stat | Sharpe | Sortino | Max DD | 2020-23 SFR | 2024-26 SFR | Cost-adjusted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| inside_value_area | 8,633 | 53.78% | 2.861 | 0.0603 | 5.86 | 1.205 | 1.842 | 0.38% | 3.471 | -2.126 | -9.139 |
| above_vah | 8,082 | 52.13% | 1.401 | 0.0016 | 2.69 | 0.571 | 0.847 | 0.56% | 1.463 | 0.949 | -10.599 |
| below_val | 5,300 | 53.53% | 3.133 | -0.0188 | 4.63 | 1.215 | 1.829 | 0.28% | 2.922 | 4.489 | -8.867 |

## Derivatives Context

OI, funding, liquidation cascades, and whale flow are unavailable in the verified spot aggTrades catalog. They were not approximated.

## Exit Research

| Exit | Events | Net expectancy | IC | T-stat | Sharpe | Sortino | Max DD | 2024-26 expectancy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed_tpsl | 22,015 | -10.700 bps | 0.0312 | -39.34 | -5.066 | -6.296 | 20.99% | -9.984 bps |
| cvd_reversal | 22,015 | -11.382 bps | 0.0171 | -52.51 | -6.762 | -8.676 | 22.17% | -11.339 bps |
| time_exit | 22,015 | -11.111 bps | 0.0126 | -27.54 | -3.546 | -6.330 | 21.73% | -8.934 bps |
| profile_exit | 22,015 | -10.992 bps | 0.0234 | -39.66 | -5.107 | -7.112 | 21.50% | -9.171 bps |
| trailing | 22,015 | -11.631 bps | 0.0070 | -37.69 | -4.853 | -6.950 | 22.59% | -10.991 bps |
| partial_dynamic | 22,015 | -11.171 bps | 0.0235 | -49.94 | -6.431 | -7.408 | 21.80% | -10.369 bps |

## Decision

- Completed-timeframe alignment is the strongest recovered feature, but its gross mean falls from 6.739 bps in 2020-2023 to 0.306 bps across only 92 recent events.
- Near-support and near-resistance rules do not improve the full-sample D4 signal; no-key-level events performed better.
- Below-POC and below-VAL contexts retain some gross structure, but neither clears explicit costs.
- Every tested exit remains negative after 12 bps round-trip cost.
- No bucket or exit is promoted from this full-sample diagnostic. Derivatives-context work requires a separately verified, timestamp-aligned historical dataset.
