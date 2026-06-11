# v85_risk_only Trade-Path Diagnostic

```json
{
  "starting_equity": 500.0,
  "ending_equity_actual": -444.7400000000015,
  "ending_equity_synthetic_1pct": 479.9276684895319,
  "gross_pnl": 320.63696000000004,
  "net_pnl": -944.74,
  "fees_paid": 1054.4808,
  "slippage_paid": 210.89616,
  "avg_win_net": 0.8655268225584595,
  "avg_loss_net": -4.591391694725028,
  "median_win": 0.85,
  "median_loss": -4.02,
  "profit_factor": 0.7690647358913499,
  "expectancy_per_trade": -0.20873619089703932,
  "expectancy_bps": -9.046900287965165,
  "turnover": 1054480.8,
  "trade_count": 4526,
  "win_rate": 0.8031374281926646,
  "loss_rate": 0.1968625718073354,
  "sharpe": -1.6050599158057375,
  "sortino": -1.69352114814958,
  "max_drawdown": 1.9586247777119175,
  "exit_reasons": {
    "PROFILE_POC_RECLAIMED": 1163,
    "TARGET": 1216,
    "PROFILE_VAL_BREAK": 788,
    "PROFILE_HARD_STOP": 213,
    "PROFILE_VAH_BREAK": 439,
    "BAR_EXIT": 545,
    "STOP": 162
  }
}
```

Counterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.
