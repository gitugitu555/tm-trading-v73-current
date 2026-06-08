# Session Log — 2026-06-08 (Gates Sweep & Win Rate Optimization)

## Repo

- **Remote:** https://github.com/gitugitu555/tm-trading-v73-current
- **Local:** `/home/tokio/tm-trading-v73-current`
- **Research PYTHONPATH:** `/home/tokio/tm-trading-research`

---

## Goals this session

1. Verify parameter settings from the latest research recommendations to push win rate up.
2. Run a parameter sweep of gates (regime, footprint, auction, approve-only permission) on the 6-month validation window without the legacy wall-clock time exit.
3. Validate promising gate combinations over the full 6-year history.
4. Log what worked and what didn't and push session updates to GitHub.

---

## What we built / ran

### Gates Parameter Sweep (168 configs)
**Script:** `scripts/v73_analyze_corrected_gates.py` (which runs `v73_sweep_corrected_gates_6m.py` in parallel using 16 workers).
**Output:** `results/v73_sweep_corrected_gates_6m_all.json` and `results/v73_sweep_corrected_gates_6m_summary.json`

### 6-Year Validation Runs
**Script:** `scripts/v73_backtest_6y_incremental.py`

---

## What worked (win rate & robust performance)

1. **Pure Baseline with 16 Volume-Bar Exit (no time exit):**
   - Disabling the legacy 5-minute timeout allows the strategy to resolve naturally via volume bars.
   - For **0.4% target**: Reached **84.81% WR** on 6 months and **72.89% WR** on 6 years (+$3,532.78 PnL, Sharpe 2.11).
   - For **0.6% target**: Reached **76.56% WR** on 6 months and **65.78% WR** on 6 years (+$5,187.03 PnL, Sharpe 2.70).
2. **Target Calibration by Objective:**
   - **0.4% target** maximizes Win Rate.
   - **0.6% target** maximizes PnL and Sharpe.

---

## What did not work (overfitting or degradation)

1. **Global Gates on Full History:**
   - Enabling `--use-regime-gate-volume-bar` or `--approve-only-permission` boosted the recent 6-month win rate (up to 85–86%).
   - However, when run on the full 6y dataset, they severely degraded performance:
     - Regime Gate (0.6% target): Win rate dropped to **61.82%**, PnL dropped to +$2,263 (vs +$5,187 baseline).
     - Approve-Only (0.4% target): Win rate dropped to **60.82%**, PnL dropped to +$3,002 (vs +$3,532 baseline).
   - **Conclusion:** Do not enable gates globally in production; treat them as regime-specific adjustments only.

---

## Code & scripts added

| Path | Change |
|------|--------|
| `scripts/v73_sweep_corrected_gates_6m.py` | Sweep 168 gate combinations on 6m window with 16 workers |
| `scripts/v73_analyze_corrected_gates.py` | Script to run gates sweep and output grouped results by target |
| `docs/SESSION_LOG_2026-06-08.md` | This log |
