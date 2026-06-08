#!/usr/bin/env python3
"""Build Tier 1 volume bars from a Nautilus ParquetDataCatalog.

This is the 'build once' foundation for the data layer.

- Sources ticks exclusively from the catalog (no more raw ZIP re-parses for bar construction).
- Produces versioned, manifested parquet files of VolumeBar records per (archive-ish or time chunk, threshold).
- Can be sharded, resumed, and is the input for cheap Tier 3 signal sweeps.
- Later can be extended to also snapshot Tier 2 features (footprint etc.) during the same pass.

Usage examples:
  python scripts/build_volume_bars.py --catalog-path data/nautilus/catalogs/btcusdt_trade_ticks_6y \
      --thresholds 300 --dest results/bars --all --progress

After build, backtests/diagnostics can read the bar parquets directly instead of re-streaming ticks.

This replaces or augments the ZIP-driven volume_bar_cvd_cache and parts of indicator_cache.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import asdict

from nautilus_trader.model.data import TradeTick
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from prime.volume_bars import VolumeBar, VolumeBarSampler
from prime.nautilus_compat import TradeTick as CompatTradeTick, InstrumentId, Price, Quantity, AggressorSide
from prime.phase4_minimal import HardRegimeClassifier
from prime.auction_state import AuctionStateEngine
from prime.configs import RegimeConfig, AuctionConfig

# For now we convert Nautilus TradeTick -> the compat one used by existing samplers/engines.
# Long term: make VolumeBarSampler accept the real Nautilus one or have a thin adapter.

INSTRUMENT = TestInstrumentProvider.btcusdt_binance()
DEFAULT_CATALOG = Path("data/nautilus/catalogs/btcusdt_trade_ticks_6y")
DEFAULT_DEST = Path("results/volume_bars")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG)
    p.add_argument("--thresholds", type=float, nargs="+", default=[300.0])
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Output dir for bar caches")
    p.add_argument("--archive", action="append", dest="archives", help="Limit to specific archive names (e.g. BTCUSDT-aggTrades-2022-09.zip style)")
    p.add_argument("--all", action="store_true", help="Process full catalog (all time)")
    p.add_argument("--start", help="Start ISO datetime or ns")
    p.add_argument("--end", help="End ISO datetime or ns")
    p.add_argument("--window-days", type=int, default=30, help="Query window size for catalog (memory safety)")
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--progress", action="store_true")
    p.add_argument("--force", action="store_true", help="Overwrite existing bar caches")
    p.add_argument("--manifest", action="store_true", default=True, help="Write/append manifest.jsonl")
    return p.parse_args()


def to_compat_tick(nt_tick: TradeTick) -> CompatTradeTick:
    """Bridge Nautilus TradeTick -> the compat Research/ChunkB style used by VolumeBarSampler today."""
    return CompatTradeTick(
        instrument_id=InstrumentId.from_str(str(nt_tick.instrument_id)),
        price=Price(float(nt_tick.price), precision=2),
        size=Quantity(float(nt_tick.size), precision=8),
        aggressor_side=AggressorSide.BUYER if nt_tick.aggressor_side.name == "BUYER" else AggressorSide.SELLER,
        trade_id=str(nt_tick.trade_id) if nt_tick.trade_id else "",
        ts_event=int(nt_tick.ts_event),
        ts_init=int(nt_tick.ts_init),
    )


def iter_catalog_ticks(
    catalog: ParquetDataCatalog,
    instrument_id: str,
    start_ns: int | None = None,
    end_ns: int | None = None,
    window_days: int = 30,
    max_rows: int | None = None,
) -> Iterable[CompatTradeTick]:
    """Yield compat ticks from catalog in safe windows. Mirrors the one in nautilus_chunkb_backtest."""
    emitted = 0
    if start_ns is None:
        first = catalog.query_first_timestamp(TradeTick, instrument_id)
        start_ns = int(first.value) if first is not None else 0
    if end_ns is None:
        last = catalog.query_last_timestamp(TradeTick, instrument_id)
        end_ns = int(last.value) if last is not None else 0

    window_ns = window_days * 24 * 60 * 60 * 1_000_000_000
    cursor = start_ns
    while cursor <= end_ns:
        upper = min(cursor + window_ns - 1, end_ns)
        batch = catalog.query(TradeTick, identifiers=[instrument_id], start=cursor, end=upper)
        for nt in batch:
            yield to_compat_tick(nt)
            emitted += 1
            if max_rows is not None and emitted >= max_rows:
                return
        cursor = upper + 1
        if not batch:
            break


def process_threshold(
    catalog: ParquetDataCatalog,
    instrument_id: str,
    threshold: float,
    dest: Path,
    start_ns: int | None,
    end_ns: int | None,
    window_days: int,
    max_rows: int | None,
    progress: bool,
    force: bool,
) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    out_name = f"bars.threshold-{int(threshold)}.parquet"
    out_path = dest / out_name

    if out_path.exists() and not force:
        print(f"  Cache exists for threshold {threshold}, skipping (use --force to rebuild)")
        # TODO: load and return summary
        return {"threshold": threshold, "skipped": True, "path": str(out_path)}

    print(f"Building bars for threshold {threshold} BTC from catalog...")

    sampler = VolumeBarSampler(threshold)
    regime = HardRegimeClassifier(**{k: v for k, v in asdict(RegimeConfig()).items()})
    auction = AuctionStateEngine(**{k: v for k, v in asdict(AuctionConfig()).items()})
    bars: list[VolumeBar] = []
    snapshots: list[dict] = []  # Tier 2 sidecar for this build run
    rows_seen = 0

    for tick in iter_catalog_ticks(
        catalog, instrument_id, start_ns, end_ns, window_days, max_rows
    ):
        rows_seen += 1
        # cheap per-tick state for Tier 2 snapshots (regime/auction) - real impl tracks 5m change properly
        regime_snap = regime.classify(price_change_5m_pct=0.0, cvd_session=0.0)
        auc_snap = auction.update(price_change_5m_pct=0.0, cvd_session=0.0)

        bar = sampler.update(tick)
        if bar is not None:
            bars.append(bar)
            snapshots.append({
                "bar_end_ts": bar.end_ts_ns,
                "regime_state": getattr(regime_snap, "state", str(regime_snap)),
                "auction_state": getattr(auc_snap, "state", str(auc_snap)),
            })
        if progress and rows_seen % 10_000_000 == 0:
            print(f"  ... {rows_seen:,} ticks, {len(bars):,} bars so far")

    if not bars:
        print(f"  No bars produced for threshold {threshold}")
        return {"threshold": threshold, "bars": 0, "rows": rows_seen}

    # Write as parquet using similar schema to existing volume_bar caches
    records = []
    for i, b in enumerate(bars):
        rec = asdict(b)
        rec["threshold_btc"] = threshold
        if i < len(snapshots):
            rec.update(snapshots[i])  # Tier 2 regime/auction snapshots (cheap, persisted with bars)
        records.append(rec)

    df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, out_path, compression="zstd")

    print(f"  Wrote {len(bars):,} bars ({rows_seen:,} ticks) to {out_path} (with {len(snapshots)} Tier2 snapshots)")

    return {
        "threshold": threshold,
        "bars": len(bars),
        "rows_seen": rows_seen,
        "path": str(out_path),
        "first_bar_ts": bars[0].start_ts_ns if bars else None,
        "last_bar_ts": bars[-1].end_ts_ns if bars else None,
    }


def main() -> int:
    args = parse_args()

    if not args.catalog_path.exists():
        print(f"Catalog not found: {args.catalog_path}")
        return 1

    catalog = ParquetDataCatalog(args.catalog_path)
    instrument_id = INSTRUMENT.id.value

    # Resolve time range (simple for now; full catalog if --all)
    start_ns = None
    end_ns = None
    # TODO: parse --start/--end into ns if provided. For MVP use full or windowed full.

    results = []
    for th in args.thresholds:
        res = process_threshold(
            catalog=catalog,
            instrument_id=instrument_id,
            threshold=float(th),
            dest=args.dest,
            start_ns=start_ns,
            end_ns=end_ns,
            window_days=args.window_days,
            max_rows=args.max_rows,
            progress=args.progress,
            force=args.force,
        )
        results.append(res)

    if args.manifest:
        manifest_path = args.dest / "manifest.jsonl"
        with open(manifest_path, "a") as f:
            for r in results:
                entry = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "builder": "build_volume_bars.py",
                    "catalog": str(args.catalog_path),
                    "result": r,
                }
                f.write(json.dumps(entry) + "\n")
        print(f"Manifest appended: {manifest_path}")

    print("Done. Bars ready for fast Tier 3 sweeps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
