#!/usr/bin/env python3
"""Precompute and cache indicators at the end of volume bars for fast backtesting."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prime.ic_harness import iter_binance_research_ticks
from prime.nautilus_compat import TradeTick, InstrumentId, Price, Quantity, AggressorSide
from prime.phase1 import (
    CVDEngine,
    DeltaVelocityEngine,
    FootprintEngine,
    SessionExtremeTracker,
    SwingDivergenceEngine,
    VWAPEngine,
)
from prime.volume_bars import VolumeBarSampler

from storage.hot_path import assert_nvme_archive, hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
INSTRUMENT = InstrumentId.from_str("BTCUSDT.BINANCE")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", action="append", dest="archives")
    parser.add_argument("--all-archives", action="store_true", default=False)
    parser.add_argument("--threshold-btc", type=float, nargs="+", default=[100.0, 200.0, 300.0])
    parser.add_argument("--cache-dir", type=Path, default=Path("results/indicator_cache"))
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--progress", action="store_true", default=False)
    parser.add_argument("--shard-count", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=None)
    return parser.parse_args()

def process_archive(
    archive: Path,
    thresholds: list[float],
    cache_dir: Path,
    max_rows: int | None = None,
    progress: bool = False,
) -> None:
    if not archive.is_file():
        print(f"Skipping missing archive: {archive}")
        return

    assert_nvme_archive(archive)
    cache_dir.mkdir(parents=True, exist_ok=True)
    for threshold in thresholds:
        suffix = f".maxrows-{max_rows}" if max_rows is not None else ""
        existing = cache_dir / f"{archive.name}.threshold-{int(threshold)}{suffix}.parquet"
        if existing.is_file():
            print(f"Cache exists, skipping {archive.name} @ {int(threshold)} BTC")
            return

    print(f"Caching indicators for {archive.name} (NVMe)...")

    # Initialize engines
    cvd_engine = CVDEngine()
    footprint_engine = FootprintEngine()
    delta_engine = DeltaVelocityEngine()
    vwap_engine = VWAPEngine()
    swing_engine = SwingDivergenceEngine()
    extreme_tracker = SessionExtremeTracker()

    samplers = {t: VolumeBarSampler(t) for t in thresholds}
    records_by_threshold: dict[float, list[dict]] = {t: [] for t in thresholds}

    rows_seen = 0
    # Stream ticks
    for tick in iter_binance_research_ticks([archive], max_rows=max_rows):
        rows_seen += 1
        ts = int(tick.ts_event)
        price = float(tick.price)
        size = float(tick.size)
        side = tick.aggressor_side

        # Standard TradeTick for base engine compatibility
        compat_tick = TradeTick(
            instrument_id=INSTRUMENT,
            price=Price(price, precision=2),
            size=Quantity(size, precision=8),
            aggressor_side=side,
            trade_id="",
            ts_event=ts,
            ts_init=ts,
        )

        # Update engines
        cvd_engine.handle_trade_tick(compat_tick)
        footprint_engine.handle_trade_tick(compat_tick)
        delta_engine.handle_trade_tick(compat_tick)
        vwap_engine.handle_trade_tick(compat_tick)
        swing_engine.update(ts, price, cvd_engine.cvd_15m)
        extreme_tracker.update(ts, price)

        # Update samplers & capture snapshots
        for threshold, sampler in samplers.items():
            bar = sampler.update(compat_tick)
            if bar is not None:
                # Capture snapshot at end of bar
                record = {
                    "start_ts_ns": bar.start_ts_ns,
                    "end_ts_ns": bar.end_ts_ns,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "buy_volume": bar.buy_volume,
                    "sell_volume": bar.sell_volume,
                    "delta": bar.delta,
                    "cumulative_delta": bar.cumulative_delta,
                    "ticks": bar.ticks,
                    
                    "cvd_5m": cvd_engine.cvd_5m,
                    "cvd_15m": cvd_engine.cvd_15m,
                    "cvd_1h": cvd_engine.cvd_1h,
                    "cvd_4h": cvd_engine.cvd_4h,
                    "cvd_session": cvd_engine.cvd_session,
                    "footprint_bias": footprint_engine.footprint_bias,
                    "footprint_stacked": footprint_engine.stacked,
                    "delta_exhaustion": delta_engine.exhaustion,
                    "vwap_deviation": vwap_engine.deviation,
                    "swing_price_high": swing_engine.price_high,
                    "swing_price_low": swing_engine.price_low,
                    "swing_cvd_high": swing_engine.cvd_high,
                    "swing_cvd_low": swing_engine.cvd_low,
                    "session_high": extreme_tracker.session_high,
                    "session_low": extreme_tracker.session_low,
                }
                records_by_threshold[threshold].append(record)

        if progress and rows_seen % 5_000_000 == 0:
            print(f"  Processed {rows_seen:,} rows...")

    # Save to Parquet
    cache_dir.mkdir(parents=True, exist_ok=True)
    for threshold, records in records_by_threshold.items():
        if not records:
            continue
        df = pd.DataFrame(records)
        suffix = f".maxrows-{max_rows}" if max_rows is not None else ""
        filename = f"{archive.name}.threshold-{int(threshold)}{suffix}.parquet"
        out_path = cache_dir / filename
        table = pa.Table.from_pandas(df)
        pq.write_table(table, out_path, compression="zstd")
        print(f"  Wrote {len(df):,} cached bars to {out_path.name}")

def main() -> int:
    args = parse_args()
    if args.archives:
        archives = sorted(args.dest / name for name in args.archives)
    elif args.all_archives:
        archives = sorted(args.dest.glob("BTCUSDT-aggTrades-*.zip"))
        archives = [a for a in archives if "_1m" not in a.name]
    else:
        print("Please specify --archive <name> or --all-archives")
        return 1

    if args.shard_count is not None and args.shard_index is not None:
        archives = [
            a for i, a in enumerate(archives)
            if i % args.shard_count == args.shard_index
        ]

    for archive in archives:
        process_archive(
            archive=archive,
            thresholds=args.threshold_btc,
            cache_dir=args.cache_dir,
            max_rows=args.max_rows,
            progress=args.progress,
        )
    return 0

if __name__ == "__main__":
    sys.exit(main())
