# Session Log — 2026-06-10 (V8.5 Grand Sweep Execution & Cache Optimization)

## Repo

- **Remote:** https://github.com/gitugitu555/tm-trading-v73-current
- **Local:** `/home/tokio/tm-trading-v73-current`
- **Research PYTHONPATH:** `/home/tokio/tm-trading-research`

---

## Goals this session

1. Execute the V8.5 master 6-year grand sweep script (`v85_grand_sweep_6y.py`) evaluating all 25 strategy families (Balanced, High-WR, wide, institutional winners, profile exit variants, param grid, gate combos).
2. Fix any resume/caching bugs in the runner script to ensure efficient incremental runs.
3. Log results and commit/push findings to GitHub.

---

## What we built / ran

### V8.5 Grand Sweep
**Script:** `scripts/v85_grand_sweep_6y.py` (evaluated 25 strategies × 132 archives = 3,300 tasks).
**Output:** `results/v85_grand_sweep_6y.json`

---

## Key findings & strategy results

All strategies were run over the full 6-year history starting with **$500 starting equity** and compounding.

### Selected Strategy Performance

| Strategy | Trades | Win Rate | Sharpe | Ending Equity | Total Return | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **v84_config2_allgates** | 0 | 0.00% | 0.0000 | $500.00 | 0.00% | Config 2 + all shadow gates (blocked all trades) |
| **v85_combined_anti** | 0 | 0.00% | 0.0000 | $500.00 | 0.00% | Profile exit + VWAP filter + score 0.50 + anti-pattern |
| **v85_all_gates** | 0 | 0.00% | 0.0000 | $500.00 | 0.00% | Profile exit + all gates active |
| **v85_risk_only** | 4,526 | 80.31% | -1.6051 | $479.93 | -4.01% | Profile exit + risk-state gate only (Best non-zero PnL) |
| **v85_vwap_filter** | 4,407 | 73.47% | -2.5017 | $472.13 | -5.57% | Profile exit + VWAP entry filter |
| **v85_wide_stop** | 6,470 | 78.22% | -1.7687 | $467.03 | -6.59% | stop=0.04 exit=36 with profile exit |
| **v85_profile_exit** | 7,416 | 74.38% | -2.1247 | $461.42 | -7.72% | Profile signal exit (POC/VWAP/VAH/VAL) |
| **v83_balanced** | 9,091 | 56.29% | -2.7703 | $454.27 | -9.15% | Legacy v8.3 baseline (t=0.005 e=24 lb=30) |

### Analysis

1. **Gate Strictness**: Combos utilizing all gates or anti-pattern filters block all trade signals. This results in no performance drawdown but zero capital utility.
2. **Win Rate vs. PnL**: Adding the risk-state gate (`v85_risk_only`) achieves a high win rate of **80.31%**, but transaction fees and slippage on the 4,526 trades result in a net return of **-4.01%**.

---

## Code & scripts updated

| Path | Change |
|------|--------|
| `scripts/v85_grand_sweep_6y.py` | Patched the cache check logic in `run_archive` to correctly reuse existing `0-trade` (0-byte `.jsonl`) files rather than re-running them. |
| `results/v85_grand_sweep_6y.json` | Master results file compiling all 25 strategy metrics. |
| `docs/SESSION_LOG_2026-06-10.md` | This log |

---

## Cache Resume Fix verification

Before the fix, running `v85_grand_sweep_6y.py` would re-run months with 0 trades, causing long execution times. Post-patch, checking the cache and loading all 3,300 tasks executes in **2.2 seconds**:

```
V8.5 Grand Sweep | 25 strategies × 132 archives = 3300 tasks | workers=24
  [  165/3300] elapsed=0s  ETA≈5s
  ...
  [ 3300/3300] elapsed=2s  ETA≈0s

All done in 2.2s
```
