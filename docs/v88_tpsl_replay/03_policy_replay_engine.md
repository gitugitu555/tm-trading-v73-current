# Policy Replay Engine

`research/v88_policy_replay.py` applies occupancy after signal generation.

Preliminary best-policy occupancy results:

| Mode | Trades | Retention | Net expectancy |
|---|---:|---:|---:|
| Independent | 820 | 99.2% | -0.000597 |
| Capped 1 | 441 | 53.3% | -0.000360 |
| Capped 2 | 644 | 77.9% | -0.000499 |

Occupancy reduces losses through selection, but no mode is positive.
