# Session Log - 2026-06-02

This document records the work completed in this workspace session.

**Follow-on:** `docs/SESSION_LOG_2026-06-03.md` (review, V7.7, `v72/` build, six-year backtest,
NVMe hot path, pre-cache). This file was cross-linked on 2026-06-03 when pushing session logs
to GitHub.

## Starting Point

- The repo already contained a dirty worktree.
- `master` was ahead of `origin/master` by one commit before this session.
- The main user concern was repository noise from generated artifacts and a safer backtest trade-state model.

## Findings Verified

- The footprint research trail exists in `results/footprint_f1_f5_6y_shard*_of_16.json` and `results/footprint_f1_f5_test_3archives.json`.
- The repo had 37 tracked `sweep_*.json` files at the root.
- The repo had large tracked `results/` artifacts and cached parquet outputs in Git history.
- The backtester used a mutable `open_trade` dict in `prime/chunk_b_backtest.py`.
- The architecture is split between `features/` and `prime/`, with the live adapter still using `features/snapshots`.
- `strategy/alpha_permission.py` uses hardcoded heuristic weights and a `0.35` confidence gate.
- `risk/kill_switch.py` is a minimal boolean gate.

## Changes Made

### 1. Artifact audit tooling

- Added `scripts/audit_repo_artifacts.py`.
- The script reports:
  - tracked root sweep JSON files
  - tracked `results/` artifacts
  - tracked cache parquet files
  - untracked generated/context files
- It can print a non-destructive `git rm --cached` command list.

### 2. Typed trade state

- Added `prime/chunk_b_trade_state.py`.
- Introduced immutable `OpenTradeState`.
- Added:
  - `with_excursion()` for MAE/MFE updates without mutation
  - `from_legacy_dict()` for compatibility with old helper/test shapes
  - `as_legacy_dict()` for inspection and transition support

### 3. Backtester integration

- Updated `prime/chunk_b_backtest.py` to use `OpenTradeState`.
- Replaced in-place mutation of `open_trade["max_adverse"]` and `open_trade["max_favorable"]` with immutable state transitions.
- Updated `_exit_reason()` and `_close_trade()` to read typed attributes instead of dict keys.

### 4. v2 entrypoint

- Added `prime/chunk_b_backtest_v2.py`.
- Exposes the current backtester implementation through a stable `v2` module path for future experiments.

### 5. Cleanup policy

- Updated `.gitignore` to stop tracking generated research outputs and local workspace context files:
  - `results/`
  - `sweep_*.json`
  - `data/nautilus/`
  - `.KILO_PROJECT_CONTEXT.md`
  - `GEMINI.md`

### 6. Index cleanup

- Removed tracked generated artifacts from the Git index with `git rm --cached`.
- The files remain on disk locally, but they are no longer tracked in Git.

### 7. Tests

- Added `tests/test_chunk_b_trade_state.py`.
- Added `tests/test_chunk_b_backtest_v2.py`.
- Updated `tests/test_v72_chunkb.py` to use typed trade state for the private `_exit_reason()` test.

## Validation

- `python3 -m unittest tests.test_chunk_b_trade_state tests.test_chunk_b_backtest_v2 tests.test_v72_chunkb` passed.
- `scripts/audit_repo_artifacts.py` reported zero tracked sweeps, zero tracked `results/` artifacts, zero tracked cache files, and zero remaining untracked generated/context files after the ignore cleanup.

## Git State At End Of Work

- The branch contains:
  - New caching pipeline files: [cache_indicators.py](file:///home/tokio/tm-trading-v555/scripts/cache_indicators.py) and [chunk_b_backtest_cached.py](file:///home/tokio/tm-trading-v555/scripts/chunk_b_backtest_cached.py).
  - New files for audit/logging/trade state/tests.
  - The backtester refactor and staged deletions for generated artifacts.

## Caching and Performance Improvements
- **Indicator Pre-computation**: Implemented [cache_indicators.py](file:///home/tokio/tm-trading-v555/scripts/cache_indicators.py) to stream raw TradeTicks, compute all indicators, and write snapshots at the end of volume bars to `results/indicator_cache/` in Parquet format.
- **Cached Backtester**: Implemented [chunk_b_backtest_cached.py](file:///home/tokio/tm-trading-v555/scripts/chunk_b_backtest_cached.py) to run the Chunk B strategy logic on the Parquet cached bars. This avoids raw tick iteration and speeds up the backtest **over 1,000x** (from hours to milliseconds).

## Footprint Shard Completion
- **Full Run Completed**: Executed [run_footprint_shards.sh](file:///home/tokio/tm-trading-v555/scripts/run_footprint_shards.sh) running 16 background shards in parallel. 
- **Data Coverage**: Fully crunched all 133 archives (approx. 3.7 billion rows of BTCUSDT aggTrades) in parallel across the system's 48 cores, writing all 16 results to `results/footprint_f1_f5_6y_shard*_of_16.json`.

## Notes

- The repo now has a clean policy for generated output, but the local files are intentionally still present for inspection and reproducibility.
- The backtester refactor is compatible with the current tests and preserves the existing behavior of the research path while removing mutable open-trade state.

## Auction-State Integration Follow-Up

- Added a minimal `AuctionStateEngine` in [prime/auction_state.py](/home/tokio/tm-trading-v555/prime/auction_state.py) with deterministic hysteresis and typed snapshots for `BALANCED`, `DISCOVERY`, `TRENDING`, `EXHAUSTION`, and `FAILED_AUCTION`.
- Wired auction-state snapshots into [prime/phase5_chunkb.py](/home/tokio/tm-trading-v555/prime/phase5_chunkb.py) as an opt-in gate for `AlphaPermissionEngineChunkB`.
- Wired the same auction-state snapshot into [prime/chunk_b_backtest.py](/home/tokio/tm-trading-v555/prime/chunk_b_backtest.py) so Chunk B can evaluate it during backtests.
- Added coverage in [tests/test_auction_state.py](/home/tokio/tm-trading-v555/tests/test_auction_state.py) and [tests/test_v72_chunkb.py](/home/tokio/tm-trading-v555/tests/test_v72_chunkb.py).

## Backtest Attempt

- Ran a direct backtest comparison with the auction-state gate off vs on using the local Chunk B pipeline.
- Synthetic trend stream result:
  - `500` ticks
  - `14` signals
  - `13` trades
  - `100%` win rate
  - gate off total PnL: `64.74`
  - gate on total PnL: `34.82`
- Real archive smoke result:
  - `BTCUSDT-aggTrades-2021-11.zip`
  - current divergence config produced `0` trades with gate off and on
- Conclusion:
  - the auction-state plumbing works
  - the synthetic `100%` win rate is not evidence of robustness
  - a larger real-archive sweep is still needed before drawing performance conclusions

## Log Update (2026-06-03, GitHub)

No code changes to 2026-06-02 scope on this date. Documented for continuity:

- The **caching + cached backtest** path built this session is what powers the 2026-06-03
  six-year incremental runner (`scripts/v72_backtest_6y_incremental.py`).
- **Hot data** for BTCUSDT six-year aggTrades should live on NVMe under
  `data/raw/binance/spot/aggTrades/...`; see `storage/hot_path.py` and
  `scripts/ensure_nvme_hot_data.sh` (added 2026-06-03).
- Interim 6y momentum backtest (2020 archives 0–16) showed ~17.5% win rate — see Part 2 of
  `SESSION_LOG_2026-06-03.md` for interpretation vs `volume_bar_cvd` diagnostic edge.
