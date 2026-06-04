# TM Trading v7.3 Current — Win Rate Improvement Program

Version: `7.3.0-CURRENT`  
Fork of: `gitugitu555/tm-trading-v555`  
Repo: `gitugitu555/tm-trading-v73-current`  
Local path: `/home/tokio/tm-trading-v73-current`

## Problem statement

The six-year momentum backtest (`signal_mode=momentum`) reports roughly **17.5% trade win rate** while the measured **volume-bar CVD divergence** signal shows **~53.3% signal-only hit rate** (300 BTC bars, 40-bar lookback, D4 HTF filter, 5-bar horizon).

That gap is not a single bug — it is **signal choice + conversion layer drift**:

| Layer | Issue |
| --- | --- |
| Signal | Backtests defaulted to momentum, not `volume_bar_cvd` |
| Entry | Tick CVD reversal confirm delayed/diluted bar-close entries |
| Permission | Fade signals penalized by `CVD_CONFIRMING` and VWAP gates |
| Exit | 300s wall-clock hold vs diagnostic 5 **volume bars** |
| Code | Duplicated volume-bar logic in cached backtest script |

## v7.3 laws

1. Protect the measured volume-bar CVD edge before adding indicators.
2. Diagnostic logic and Chunk B must share `prime/volume_bar_cvd.py`.
3. Report signal hit rate and trade win rate separately.
4. Each stage gets a git checkpoint pushed to GitHub.

## Staged program

### Stage 1 — Alignment (checkpoint `stage-1-alignment`) ✅

- [x] New repo `tm-trading-v73-current`
- [x] Shared `VolumeBarCVD` engine module
- [x] Skip CVD tick confirm for `volume_bar_cvd`
- [x] Permission: no CVD-confirm / VWAP penalty on volume-bar path
- [x] `exit_after_volume_bars` exit (default 5 in v73 runner)
- [x] `scripts/v73_backtest_6y_incremental.py` with correct CLI profile

### Stage 2 — Conversion tuning (checkpoint `stage-2-conversion`) ✅

- [x] Fade-aware auction multipliers (`phase5_chunkb.py`)
- [x] Regime gate on volume-bar (`--use-regime-gate-volume-bar`, on in v73 runner)
- [x] Fee-aware TP/SL: stop 0.45%, target 0.25%
- [x] Auction gate default on for v73 6y
- [x] Parquet cache symlink → v555 `results/indicator_cache` (reuse Codex pre-cache)
- [x] `scripts/v73_conversion_sweep.py`

Pending:

- D5 delta-reversal entry

### Stage 3 — Filters & scorecards

- Signal-only `SignalScorecard` separate from trade PnL
- `ExperimentManifest` on every sweep
- Footprint F3/F5 confluence filters

### Stage 4 — Consolidation

- `features/` thin adapters over `prime/`
- CI installs full `pyproject.toml` deps

## Research synthesis (sub-agents)

Four parallel research passes completed 2026-06-04:

1. **Volume-bar CVD** — align HTF, disable confirm, bar-count exits, shared engine
2. **Auction state** — mode-specific permission matrix; enable with ablation
3. **Exits / permission** — target/stop calibration; do not conflate signal WR with trade WR
4. **Regime / features** — gate volume-bar like divergence; VPIN/footprint as filters

Full reports are embedded in agent transcripts; actionable items are staged above.

## Commands

```bash
cd /home/tokio/tm-trading-v73-current
.venv/bin/python -m unittest -q

# Single-archive smoke (requires NVMe data + cache)
.venv/bin/python scripts/chunk_b_backtest_cached.py \
  --archive BTCUSDT-aggTrades-2022-09.zip --max-rows 500000 \
  --signal-mode divergence --divergence-type volume_bar_cvd \
  --threshold-btc 300 --divergence-lookback-bars 40 \
  --exit-after-volume-bars 5 --no-use-cvd-reversal-confirm

# Full 6y profile (resume-capable)
.venv/bin/python scripts/v73_backtest_6y_incremental.py --resume
```

## Upstream

Improvements that belong in both repos after validation should be cherry-picked into `tm-trading-v555` per V7.7 roadmap.