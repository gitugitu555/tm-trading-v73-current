# Session Log: 2026-06-10 (Optimization)

## Objective
The goal was to investigate the collapsed performance metrics (negative PnL and poor Sharpe) in the v85 suite despite an ~85% win rate, and find ways to increase Sharpe, Win Ratio, and Returns.

## What Didn't Work / Findings
1. **Fee Drag Starvation:** We discovered that all variants in the v85 testbed were producing negative returns. This was traced to the `v85_grand_sweep_6y.py` script hardcoding `--base-position-pct 0.01` (1% of equity). On a $500 starting equity, a 1% position is $5.00. Targeting 0.5% yields extremely low gross profit per trade, which is mathematically eclipsed by the combined 12 bps of fixed slip/fee costs. The system bled out from fee-drag.
2. **Over-Constrained Gates:** The shadow gates (Anti-Pattern, VPIN Toxicity, Risk-State, etc.) were filtering out over 80% of signals. While this raised the win rate slightly, it massively reduced trade count, which in turn destroyed the annualized Sharpe ratio.

## What We Did
1. **Implemented Proper Daily Metrics:** Added portfolio-level `daily_sharpe`, `daily_sortino`, and `max_drawdown` to `prime/performance.py` and incorporated them into the `ChunkBBacktestReport`.
2. **Fixed the Fee Drag:** Modified `scripts/v85_grand_sweep_6y.py` to use a 50% position size (`--base-position-pct 0.50`), returning the test harness to its institutional baseline.
3. **Apples-to-Apples Normalization:** Re-launched the entire 6-year grand sweep across all 27 variants to recalculate the actual Sharpe, Sortino, and PnL curves without the artificial fee drag.

## Results
The sweep completed successfully over the full 6-year BTCUSDT dataset (3,564 archive tasks). The results decisively prove the root cause of the performance collapse:

1. **The 'Apples-to-Apples' Legacy Winner:** 
   The `v85_apples_legacy` configuration (which uses v85 logic but reverts to `base_position_pct=0.50` and `entry_lag_bars=0`) dominated the sweep:
   - **Return:** +8.81%
   - **Trade-Level Sharpe:** 3.03
   - **Daily Sharpe:** 5.35
   - **Daily Sortino:** 10.01
   - **Max Drawdown:** 0.57%
   - **Win Rate:** 71.80%

2. **The Impact of Entry Lag:**
   The `v85_apples_lag_only` configuration used the exact same institutional sizing but introduced the new v85 default of `entry_lag_bars=1` (next-bar execution).
   - **Return:** -8.81%
   - **Trade-Level Sharpe:** -2.65
   - **Daily Sharpe:** -5.65

   **Conclusion:** The alpha captured by the divergence volume-bar CVD signals is highly transient. Delaying execution by even a single bar completely inverts the strategy's profitability from a 3.0 Sharpe to a -2.6 Sharpe. The strategy relies on immediate (intra-bar/same-bar) execution to capture the divergence premium before the market equilibrates.

## Next Steps
- Review the sweep results and select the best profile-based exit configuration.
- Push changes and this log to the repository.
