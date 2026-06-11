# v85_apples_lag_only Trade-Path Diagnostic

```json
{
  "starting_equity": 500.0,
  "ending_equity_actual": -1358.680000000056,
  "ending_equity_synthetic_1pct": 455.96677113947436,
  "gross_pnl": 346.9186560000002,
  "net_pnl": -1858.6799999999998,
  "fees_paid": 1837.99888,
  "slippage_paid": 367.599776,
  "avg_win_net": 0.8064882742032472,
  "avg_loss_net": -1.4701949512621844,
  "median_win": 1.02,
  "median_loss": -0.8,
  "profit_factor": 0.6840188703302308,
  "expectancy_per_trade": -0.20626789479525023,
  "expectancy_bps": -10.227861908425874,
  "turnover": 1837998.88,
  "trade_count": 9011,
  "win_rate": 0.553656641882144,
  "loss_rate": 0.44401287315503274,
  "sharpe": -2.6538097846655533,
  "sortino": -2.8714002177592546,
  "max_drawdown": 3.7212531079066222,
  "exit_reasons": {
    "TARGET": 4018,
    "BAR_EXIT": 4938,
    "STOP": 55
  }
}
```

Counterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.
