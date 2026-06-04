# V7.2 Staged Build (Modular, No Backtest)

Version: `7.2.0-STAGED`

Active implementation package: `v72/`

Backtesting and PnL proof are **out of scope** for this track. Another process
owns Chunk B backtests. This build produces **swappable, testable stages** that
emit structured signals, permissions, and trade intents only.

## Stage Map

| Stage | Module | Responsibility | Can disable? |
| --- | --- | --- | --- |
| S0 | `v72/stages/s0_truth.py` | Trade signing + data quality firewall | No |
| S1 | `v72/stages/s1_flow.py` | CVD, footprint, delta, VWAP microstructure | No |
| S2 | `v72/stages/s2_book.py` | L2 book intelligence (VPIN, spoof, whale) | Yes |
| S3 | `v72/stages/s3_regime.py` | Hard regime classifier | Yes |
| S4 | `v72/stages/s4_signal.py` | `CVDMomentumConfirmation` signal (V720) | Yes |
| S5 | `v72/stages/s5_permission.py` | AlphaPermission multiplier chain | Yes |
| S6 | `v72/stages/s6_memory_risk.py` | Kill switch + setup memory export | Yes |

## Default Order

```text
S0 -> S1 -> [S2] -> S3 -> S4 -> S5 -> S6
```

Reorder in `V72PipelineConfig.stage_order` for experiments. Each stage reads and
returns `V72PipelineState` without hidden globals.

## V7.2 Rules (from active spec)

1. Phase 0 signing and firewall before any feature work.
2. Phase 1 engines are event-driven on `TradeTick`.
3. Chunk B **momentum** path uses `CVDMomentumConfirmation` — divergence is not
   the primary entry signal (modifier only).
4. Nautilus strategy shell: `register_indicator_for_trade_ticks()` per V720.
5. No orders in the staged pipeline; intents only.

## Commands

```bash
cd /home/tokio/tm-trading-v555
.venv/bin/python -m unittest tests.test_v72_pipeline_stages -v
.venv/bin/python scripts/v72_pipeline_demo.py
```

## Exit Criteria (this track)

- [x] All `test_v72_pipeline_stages` tests pass
- [x] Pipeline demo runs on synthetic ticks without backtest imports
- [x] Each stage can be disabled independently in config
- [x] Nautilus `CVDMomentumConfirmation` imports without `ChunkBBacktester`

## Not In This Track

- `scripts/chunk_b_backtest.py`
- `scripts/chunk_b_sweep.py`
- PnL, Sharpe, DSR, or trade simulation