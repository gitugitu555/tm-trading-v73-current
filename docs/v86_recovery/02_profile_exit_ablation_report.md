# Profile Exit Ablation Report

Status: pending controlled execution.

Profile exits run before TPSL and profile mode triples the normal bar-exit safety horizon. Both effects must be separated from individual POC/VAH/VAL rules.

## Preliminary Historical-Ledger Evidence

| Exit reason | Trades | Net PnL | Expectancy/trade |
|---|---:|---:|---:|
| `PROFILE_POC_RECLAIMED` | 1,564 | +1,251.51 | +0.8002 |
| `PROFILE_VAL_BREAK` | 1,443 | +974.46 | +0.6753 |
| `PROFILE_VAH_BREAK` | 969 | +642.62 | +0.6632 |
| `BAR_EXIT` | 1,526 | -2,561.53 | -1.6786 |
| `PROFILE_HARD_STOP` | 276 | -2,092.07 | -7.5800 |
| `STOP` | 186 | -1,311.66 | -7.0519 |

POC reclaim is not the primary realized loss source. Whether it clipped later winners remains unknown because historical ledgers lack post-exit counterfactual paths.
