# Project Log

This document is a curated log of the work done in this workspace.

## Repository And Research Stack

- Established a deterministic research scaffold around the V7.2 Nautilus-Prime target.
- Kept feature logic in pure engines and boundary adapters separate.
- Preserved unit tests for the core signal engines and replay-related components.

## Footprint And Backtest Work

- Investigated the `footprint_f1_f5_diagnostic.py` backtest runner.
- Confirmed that long-running shard jobs were interrupted by reboot rather than completing.
- Verified that the existing shard outputs were placeholders and not completed 6y results.
- Timed a reduced sample run against the BTCUSDT dataset to gauge throughput.
- Captured the footprint smoke result set in `results/footprint_f1_f5_test_3archives.json` and the 6y shard outputs under `results/footprint_f1_f5_6y_shard*_of_16.json`.
- Rebuilt the BTC hot working set onto NVMe so the repeated footprint and Nautilus runs no longer resolve through the Seagate symlink.
- Validated the Nautilus-backed BTC smoke backtest against `data/nautilus/catalogs/btcusdt_trade_ticks_6y` after the hot-path fix.
- Launched a full 6y BTC catalog rebuild in the background from the local hot copy so the Parquet-backed backtests can resume on a clean catalog.

## Data Storage Work

- Moved BTCUSDT aggTrades archives to Seagate cold storage at `/mnt/seagate/tm-trading-v555/data/raw`.
- Left a symlink at the original project path so existing scripts continued to work.
- Added `docs/DATA_LAYOUT.md` to define the canonical dataset path scheme.
- Added `storage/dataset_layout.py` so hot and cold dataset paths are computed consistently.
- Added `scripts/binance_data_manager.py` to inspect, link, sync, and promote datasets.
- Replaced the BTC hot-path symlink with a real NVMe copy at `/home/tokio/tm-trading-v555/data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21`.
- Confirmed the 6y Parquet catalog is now hosted under `/home/tokio/tm-trading-v555/data/nautilus/catalogs/btcusdt_trade_ticks_6y`.

## Download Workflow Work

- Updated the BTCUSDT download scripts to default to the cold-storage root.
- Preserved override support through `DEST` and `TM_DATA_COLD_ROOT`.
- Kept the existing aria2 and curl-based workflows intact, only changing the default target root.

## Validation Work

- Ran unit tests for the new dataset manager helpers.
- Verified the new CLI help output for the dataset manager.
- Confirmed the BTCUSDT dataset status against the cold-storage-backed path.
- Ran shell syntax checks on the updated download scripts.
- Ran a Nautilus smoke backtest against the 6y BTC catalog with the project venv and confirmed the backtest path is functional.

## Backtest Execution Work

### Volume-Bar CVD Diagnostic (D1-D5 Divergence Track & Horizon Sweeps)
- **Status**: ✅ COMPLETED
- **Script**: `scripts/volume_bar_cvd_diagnostic.py`
- **Dataset**: 133 archives, 3,735,879,540 rows (BTCUSDT aggTrades 2020-05-22 to 2026-05-21)
- **Configuration**: thresholds [100, 200, 300], lookbacks [20, 30, 40], horizons [3, 5, 10]
- **Stages Tested**: D1_divergence, D2_delta_rev_2, D3_delta_rev_3, D4_htf, D5_delta_rev_2_htf
- **Results**:
  - Best performer: **D4_htf @ 300/40/h5** → IC=0.0519, Hit Rate=53.29%, Mean SFR=0.00024894, Events=22,506
  - Validated V76 roadmap claim exactly
  - Full report: `results/volume_bar_cvd_diagnostic_D1-D5_BACKTEST_REPORT.md`
  - Raw data: `results/volume_bar_cvd_6y.json`
  - Cache: `results/volume_bar_cvd_cache/` (133 parquet files)

### Footprint F1-F5 Diagnostic
- **Status**: ✅ COMPLETED
- **Script**: `scripts/footprint_f1_f5_diagnostic.py` and `scripts/run_footprint_shards.sh`
- **Dataset**: 133 archives (approx. 3.7 billion rows of BTCUSDT aggTrades)
- **Results**: Complete 16-shard execution outputs generated under `results/footprint_f1_f5_6y_shard*_of_16.json`

## GitHub And Collaboration Notes

- Avoid storing GitHub tokens in the repo or pasting them into chat.
- Prefer SSH or `gh auth login` for persistent GitHub access.
- If a token must be used locally, keep it only in the shell environment or a restricted local file.
- Added `scripts/git_shared_setup.sh` to normalize local Git identity for whichever user is active.

## L2 Data Decision Notes

- Reviewed the best next dataset for deep backtesting of imbalance, spoofing, iceberg, and execution-quality features.
- Concluded that Bybit should be the primary L2 source because its public orderbook feed supports snapshot plus delta reconstruction with sequencing fields and deeper book levels.
- Kept Binance as the secondary venue because the repo already has strong Binance-based research history and it is useful for cross-venue validation.
- Agreed that raw book updates plus trades matter more than snapshot-only archives or precomputed metric pipelines for this stage.
- Recommended capture order:
  - Bybit BTCUSDT perp L2 first
  - Binance BTCUSDT spot/perp next
  - Expand to cross-venue and longer windows after replay parity is proven

## Bybit Capture Work

- Started the six-year Bybit BTCUSDT trade-history pull into `data/raw/bybit/trading/BTCUSDT/` using the public Bybit history downloader.
- Started the available Bybit BTCUSDT orderbook capture window from `2025-05-01` through `2026-05-31` into parquet under `data/parquet/bybit/orderbook/BTCUSDT/`.
- Confirmed the orderbook source only provides historical L2 coverage from May 2025, so the six-year span is only available for trades, not orderbook depth.
- Chose the streaming parquet orderbook path because it is the usable format for replay and feature work, and it keeps the capture directly aligned with imbalance and spoofing research.

## Session Summary

- Narrowed the free-data search to sources that are actually usable for replay, not just marketing claims.
- Verified OKX as the strongest free official historical market-data portal found in this session, with tick trade history from September 2021 and L2 order book history from March 2023.
- Reconfirmed that Bybit public history is useful for trades and recent orderbook work, but not for a full six-year L2 archive.
- Started the Bybit BTCUSDT six-year trade pull and the available Bybit BTCUSDT orderbook window so the repo has immediate data to test against.
