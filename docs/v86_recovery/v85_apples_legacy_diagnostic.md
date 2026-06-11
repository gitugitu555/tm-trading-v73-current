# v85_apples_legacy Trade-Path Diagnostic

```json
{
  "starting_equity": 500.0,
  "ending_equity_actual": 2427.4299999999243,
  "ending_equity_synthetic_1pct": 544.0357006080555,
  "gross_pnl": 4210.574468,
  "net_pnl": 1927.43,
  "fees_paid": 1902.62039,
  "slippage_paid": 380.524078,
  "avg_win_net": 0.902248327622777,
  "avg_loss_net": -1.4997710241465445,
  "median_win": 1.1,
  "median_loss": -0.78,
  "profit_factor": 1.535033102471929,
  "expectancy_per_trade": 0.22556231714452898,
  "expectancy_bps": 9.879907000044756,
  "turnover": 1902620.39,
  "trade_count": 8545,
  "win_rate": 0.7172615564657695,
  "loss_rate": 0.28110005851375075,
  "sharpe": 3.026731313928887,
  "sortino": 3.5883609496101045,
  "max_drawdown": 0.05757116928243875,
  "exit_reasons": {
    "TARGET": 5245,
    "BAR_EXIT": 3262,
    "STOP": 38
  }
}
```

Counterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.
