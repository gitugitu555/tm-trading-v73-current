# Gate Shadow Value Report

Status: pending shadow-ledger execution.

No gate can be promoted from trade count or win rate. Required accounting is blocked winners, blocked losers, their PnL, net gate value, and retention.

## Preliminary Matched-Ledger Evidence

| Candidate | Allowed | Blocked | Blocked winners | Blocked losers | Net gate value | Retention |
|---|---:|---:|---:|---:|---:|---:|
| `v84_config2_profile` | 9,089 | 2 | 0 | 2 | +0.96 | 99.978% |
| `v84_config2_allgates` | 0 | 9,091 | 5,105 | 3,966 | +1,941.18 | 0% |

The market-profile gate has negligible positive historical shadow value and needs year/regime stability testing. The all-gates stack is rejected because it blocks every trade, regardless of nominal blocked-loss value.
