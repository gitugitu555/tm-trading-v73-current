# V9.2 Research Run Manifest Specification

## Purpose
If a runner does not construct daily equity, then daily Sharpe claims are invalid for that runner. All official backtests must emit a standardized set of outputs to prevent metric fabrication.

## Required Outputs
Every official research run must write the following files to its output directory:

1. `equity_curve_by_trade.csv`
2. `calendar_daily_equity.csv`
3. `daily_returns.csv`
4. `trade_log.csv`
5. `run_manifest.json`

## Manifest JSON Schema (`run_manifest.json`)
The manifest must include the precise state of the parameters and the code when the run was executed. 

```json
{
  "commit_hash": "string (git rev-parse HEAD)",
  "branch": "string (current git branch)",
  "script_name": "string (e.g. scripts/v91_verified_signal_purity.py)",
  "config_path": "string (optional, path to sweep json)",
  "symbol": "string (e.g. BTCUSDT)",
  "date_range": {
    "start": "string (YYYY-MM-DD)",
    "end": "string (YYYY-MM-DD)"
  },
  "bar_type": "string (e.g. volume, time, footprint)",
  "bar_size": "integer/float (e.g. 500 BTC, 15m)",
  "fees": {
    "bps_per_side": "float",
    "model": "string (maker/taker)"
  },
  "slippage": {
    "bps_per_side": "float"
  },
  "entry_lag": "integer (number of bars)",
  "stop_pct": "float (e.g. 0.03 for 3%)",
  "target_pct": "float (e.g. 0.01 for 1%)",
  "exit_model": "string (e.g. fixed_tpsl, cvd_reversal, dynamic_atr)",
  "position_sizing_model": "string (e.g. fixed_fractional, 1_contract)",
  "random_seed_if_any": "integer or null"
}
```

## Scoreboard Metrics
The official scoreboard must prioritise these metrics derived from the standard outputs:
1. net expectancy after costs
2. calendar-daily Sharpe
3. max drawdown
4. 2024–2026 out-of-sample behaviour

**Do not use per-trade annualised Sharpe as a primary decision metric.**
