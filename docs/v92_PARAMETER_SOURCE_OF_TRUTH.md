# V9.2 Parameter Source of Truth

## Purpose
This document audits and standardizes the chaotic parameter spread across the repository's backtesting scripts. It establishes the single source of truth for all future research runs.

## 1. Audit of Current Runners & Defaults

### Legacy `chunk_b` / V7.3 Scripts
- `scripts/chunk_b_backtest.py`
- `scripts/chunk_b_backtest_cached.py`
- `scripts/nautilus_chunkb_backtest.py`
- `scripts/chunk_b_sweep.py`
- `prime/chunk_b_backtest.py`
- `prime/configs.py`
**Defaults Found:**
- `stop_pct`: 0.003 (0.3%)
- `vwap_structure_pct`: 0.003
- `session_extreme_pct`: 0.003
**Issues:** These heavily hardcode or default to a 0.3% stop loss which is tight. Target percentages vary widely or aren't consistently explicitly defaulted here.

### V8.3 / V8.4 Sweep Scripts
- `scripts/v83_backtest_6y.py`
- `scripts/v84_backtest_6y_parallel.py`
- `scripts/v84_sweep_institutional.py`
**Defaults Found:**
- `target_pct`: 0.003 in V8.3
- `stop_pct`: 0.03 (3.0%) hardcoded in institutional sweep.
**Issues:** Mismatched stop loss scales between V7 and V8 (0.3% vs 3.0%).

### V8.6 / V9.0 Explicit Replay & Cost Scripts
- `scripts/v86_controlled_ablation.py`
- `scripts/v90_explicit_fee_slippage_replay.py`
**Defaults Found:**
- Fees: 0 to 15 bps tested.
- Slippage: 0 to 3 bps tested.
- Fixed TPSL Baseline in V90: `target_pct=0.0055`, `stop_pct=0.03`.
**Issues:** Better cost handling, but still floating configurations.

### The Claude Identified Anomaly
- Claude observed a test configuration of `stop_pct=0.003`, `target_pct=0.006` (0.30% stop, 0.60% target).
- This exact pair was found in `scripts/v73_conversion_sweep.py` labelled as `legacy_tpsl`.

## 2. Official Research Parameters (V9.2+)

**Official Runner:**
`scripts/v91_verified_signal_purity.py` and upcoming `scripts/v91_d4_bar_horizon_surface.py` are the official research foundations. No TP/SL, fees, slippage, position occupancy, entry lag, or trade-exit logic is used for signal-purity benchmarks.

**When executing explicitly with costs (Phase 4+), the runner must adhere to:**
- **Fee Model:** Maker/Taker explicitly defined. (e.g. Maker 0bps / Taker 5bps per side).
- **Slippage Model:** 1-2 bps per side for taker entries/exits depending on liquidity.
- **Fixed TP/SL Base:** 
  - Do not default to `stop_pct=0.003` unless part of a sweep.
  - If a fixed setup is required, it must be explicitly declared in the manifest.

## 3. Deprecated Scripts
All `chunk_b_*.py` and `v73_*.py` and `v84_*.py` scripts are hereby marked as deprecated for official alpha reporting. They can be used for reference but their outputs must not be used to justify strategy revival.
