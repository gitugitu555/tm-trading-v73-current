# v85_profile_exit Trade-Path Diagnostic

```json
{
  "starting_equity": 500.0,
  "ending_equity_actual": -1243.9100000000042,
  "ending_equity_synthetic_1pct": 461.4199311417698,
  "gross_pnl": 216.07854799999998,
  "net_pnl": -1743.91,
  "fees_paid": 1633.32379,
  "slippage_paid": 326.664758,
  "avg_win_net": 0.7682398838686264,
  "avg_loss_net": -3.1511228255139696,
  "median_win": 0.69,
  "median_loss": -2.02,
  "profit_factor": 0.7082630719610284,
  "expectancy_per_trade": -0.23515507011866235,
  "expectancy_bps": -10.823085368466124,
  "turnover": 1633323.79,
  "trade_count": 7416,
  "win_rate": 0.7431229773462783,
  "loss_rate": 0.2557982740021575,
  "sharpe": -2.124665497254795,
  "sortino": -2.231314346173365,
  "max_drawdown": 3.4790608510049683,
  "exit_reasons": {
    "PROFILE_POC_RECLAIMED": 1564,
    "PROFILE_VAH_BREAK": 969,
    "TARGET": 1452,
    "PROFILE_VAL_BREAK": 1443,
    "PROFILE_HARD_STOP": 276,
    "STOP": 186,
    "BAR_EXIT": 1526
  }
}
```

Counterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.
