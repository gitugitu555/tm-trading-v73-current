# v84_config2 Trade-Path Diagnostic

```json
{
  "starting_equity": 500.0,
  "ending_equity_actual": -1441.1800000000185,
  "ending_equity_synthetic_1pct": 454.2666714300111,
  "gross_pnl": 281.82300000000004,
  "net_pnl": -1941.18,
  "fees_paid": 1852.5025,
  "slippage_paid": 370.5005,
  "avg_win_net": 0.767898139079334,
  "avg_loss_net": -1.4778870398386283,
  "median_win": 0.96,
  "median_loss": -0.8,
  "profit_factor": 0.6688140856124067,
  "expectancy_per_trade": -0.21352766472335277,
  "expectancy_bps": -10.548798708346457,
  "turnover": 1852502.5,
  "trade_count": 9091,
  "win_rate": 0.5615443845561544,
  "loss_rate": 0.43625563744362555,
  "sharpe": -2.770322263503119,
  "sortino": -2.976747499540432,
  "max_drawdown": 3.889614007162789,
  "exit_reasons": {
    "TARGET": 4190,
    "BAR_EXIT": 4773,
    "STOP": 128
  }
}
```

Counterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.
