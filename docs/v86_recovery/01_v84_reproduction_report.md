# V8.4 Reproduction Report

Status: pending controlled execution.

The measurement audit already proves historical and V8.5 summaries are not directly comparable: V8.5 grand-sweep ending equity is a synthetic 1% reconstruction while its runner emits 50%-sized compounded trade PnL. Use `scripts/v86_controlled_ablation.py --execute --labels v86_00_v84_repro_lag0 v86_01_v84_repro_lag1 v86_02_v84_repro_lag1_cost0 v86_03_v84_repro_lag1_cost1x v86_04_v84_repro_lag1_cost2x v86_05_v84_repro_lag1_cost3x`.

## Preliminary Existing-Cache Comparison

| Label | Entry lag | Trades | Win rate | Sharpe | Emitted-ledger net PnL |
|---|---:|---:|---:|---:|---:|
| `v85_apples_legacy` | 0 | 8,545 | 71.73% | 3.0267 | +1,927.43 |
| `v85_apples_lag_only` | 1 | 9,011 | 55.37% | -2.654 | -1,858.68 |

The existing labels show a large runner-output break. They are not a clean timing comparison: V8.7 found only 2,890 common signal IDs, while 5,655 signals appear only in Lag 0 and 6,121 only in Lag 1. Lag mode changes position occupancy and the evaluated/taken opportunity set. These archive ledgers also reset equity per archive, so summed emitted PnL is diagnostic rather than a valid globally compounded ending equity.
