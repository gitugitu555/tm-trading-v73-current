# Project Roadmap

This roadmap captures the current state of the repo and the next practical steps.

## Current State

- Deterministic feature engines exist for trade signing, CVD, delta, footprint, VPIN, microprice, L2 imbalance, absorption, spoofing, iceberg detection, and whale pressure.
- The V7.2 Nautilus-Prime path is the active implementation target.
- Sample-first IC and research diagnostic scripts exist for BTCUSDT aggTrades.
- Raw Binance BTCUSDT aggTrades archives are now stored on Seagate cold storage by default, with a hot-cache symlink at the original project path.
- A small dataset manager exists to keep cold storage and hot cache aligned.

## Near-Term Goals

1. Add support for additional symbols and tick sources using the same dataset layout.
2. Keep hot-cache copies only for the datasets currently under active backtest.
3. Extend the download scripts so new instruments default to cold storage.
4. Add benchmark comparisons for zipped versus unzipped input on HDD and SSD/NVMe.
5. Keep backtest outputs and research diagnostics reproducible and shardable.

## Mid-Term Goals

1. Expand the replay and research workflow beyond BTCUSDT into other major pairs.
2. Add structured manifests for each dataset with source, date range, and verification metadata.
3. Build a repeatable sync process for cold storage to hot cache promotion.
4. Use the same storage conventions for futures, spot, and other tick feeds.

## Longer-Term Goals

1. Keep the research path deterministic and explainable before any live execution work.
2. Use reason-coded output for every alpha gate and rejection.
3. Preserve a clean separation between raw data, hot cache, results, and strategy code.
4. Keep the repo ready for GitHub collaboration and review.

## Expansion Phase

Expansion work starts only after the active V7.7 replay, no-lookahead, parity,
and signal-to-trade validation gates pass. Expansion modules remain passive
diagnostics until walk-forward and out-of-sample evidence supports promotion.

Current expansion research:

- V8.2.1 Qwen validation addendum: true multi-level MLOFI, VPIN construction
  comparisons, MAE/MFE trade-path research, and shadow-gate promotion criteria
  (`docs/V82_1_QWEN_VALIDATION_ADDENDUM.md`)
- Multi-symbol and cross-venue validation after the single-symbol research path
  is reproducible
- Advanced models only after deterministic diagnostics and labelled datasets
  are trustworthy

## Future Blueprints

- V7.4 auction-state blueprint: `docs/V74_AUCTION_STATE_ENGINE_BLUEPRINT.md`
- V7.5 master roadmap: `docs/V75_MASTER_ROADMAP.md`
- V7.6 SWOT and edge roadmap: `docs/V76_SWOT_EDGE_ROADMAP.md`
- V8.2.1 Qwen validation addendum: `docs/V82_1_QWEN_VALIDATION_ADDENDUM.md`
- Multi-agent automation roadmap: `docs/MULTI_AGENT_AUTOMATION_ROADMAP.md`
