#!/usr/bin/env python3
"""Load Binance BTC aggTrades into a Nautilus Parquet catalog and render a chart.

This is a lightweight bridge from the current ZIP-based research data to a
NautilusTrader-compatible catalog. It is intentionally simple:

- reads Binance aggTrades ZIP files
- converts rows into Nautilus `TradeTick` objects
- persists them in a `ParquetDataCatalog`
- writes a small Plotly HTML chart for visual inspection

Use `--all-archives` to ingest the full 6-year dataset, or keep the default
single-archive demo for a quick smoke test.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import plotly.graph_objects as go

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.test_kit.providers import TestInstrumentProvider


DEFAULT_DEST = Path("data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21")
DEFAULT_CATALOG = Path("data/nautilus/catalogs/btcusdt_trade_ticks")
DEFAULT_HTML = Path("results/nautilus_btcusdt_trade_ticks.html")
DEFAULT_CHUNK_SIZE = 200_000
DEFAULT_SAMPLE_POINTS = 20_000
CSV_COLUMNS = [
    "trade_id",
    "price",
    "quantity",
    "a",
    "b",
    "timestamp",
    "buyer_maker",
    "ignore",
]


@dataclass(frozen=True)
class LoadStats:
    archives: int = 0
    rows: int = 0
    ticks: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--archive", action="append", dest="archives")
    parser.add_argument("--all-archives", action="store_true", default=False)
    parser.add_argument("--include-special-1m", action="store_true", default=False)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--sample-points", type=int, default=DEFAULT_SAMPLE_POINTS)
    parser.add_argument("--max-archives", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--rebuild", action="store_true", default=False)
    parser.add_argument("--progress", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archives = select_archives(args)
    if not archives:
        raise SystemExit("No archives selected")

    if args.rebuild and args.catalog_path.exists():
        import shutil

        shutil.rmtree(args.catalog_path)

    args.catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(args.catalog_path)
    instrument = TestInstrumentProvider.btcusdt_binance()
    catalog.write_data([instrument])

    stats = LoadStats()
    total_rows_limit = args.max_rows
    total_rows_seen = 0

    for archive in archives:
        archive_rows, archive_ticks = ingest_archive(
            archive=archive,
            catalog=catalog,
            instrument_id=instrument.id,
            chunk_size=args.chunk_size,
            row_limit=None if total_rows_limit is None else max(total_rows_limit - total_rows_seen, 0),
            progress=args.progress,
        )
        if archive_rows == 0:
            continue
        stats = LoadStats(
            archives=stats.archives + 1,
            rows=stats.rows + archive_rows,
            ticks=stats.ticks + archive_ticks,
        )
        total_rows_seen += archive_rows
        if args.progress:
            print(
                f"imported {archive.name} rows={archive_rows:,} ticks={archive_ticks:,}",
                flush=True,
            )
        if total_rows_limit is not None and total_rows_seen >= total_rows_limit:
            break

    start_ts = catalog.query_first_timestamp(TradeTick, instrument.id.value)
    end_ts = catalog.query_last_timestamp(TradeTick, instrument.id.value)
    start_ns = int(start_ts.value) if start_ts is not None else None
    end_ns = int(end_ts.value) if end_ts is not None else None
    points = catalog.trade_ticks([instrument.id.value], start=start_ns, end=end_ns)
    html_path = render_chart(points, args.html, args.sample_points)

    summary = {
        "catalog_path": str(args.catalog_path),
        "instrument": instrument.id.value,
        "archives_processed": stats.archives,
        "rows_seen": stats.rows,
        "ticks_written": stats.ticks,
        "first_ts_ns": start_ns,
        "last_ts_ns": end_ns,
        "html": str(html_path),
    }
    summary_path = args.html.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def select_archives(args: argparse.Namespace) -> list[Path]:
    if args.archives:
        archives = sorted(args.dest / name for name in args.archives)
    elif args.all_archives:
        archives = sorted(args.dest.glob("BTCUSDT-aggTrades-*.zip"))
        if not args.include_special_1m:
            archives = [archive for archive in archives if "_1m" not in archive.name]
    else:
        archives = [args.dest / "BTCUSDT-aggTrades-2020-05-22.zip"]

    if args.max_archives is not None:
        archives = archives[: args.max_archives]
    return archives


def ingest_archive(
    *,
    archive: Path,
    catalog: ParquetDataCatalog,
    instrument_id,
    chunk_size: int,
    row_limit: int | None,
    progress: bool,
) -> tuple[int, int]:
    if not archive.is_file() or row_limit == 0:
        return 0, 0

    csv_name = archive.name.removesuffix(".zip") + ".csv"
    rows_seen = 0
    ticks_written = 0

    with ZipFile(archive) as zipped:
        with zipped.open(csv_name) as raw:
            reader = pd.read_csv(
                raw,
                header=None,
                names=CSV_COLUMNS,
                chunksize=chunk_size,
            )
            for idx, chunk in enumerate(reader, start=1):
                if row_limit is not None:
                    remaining = row_limit - rows_seen
                    if remaining <= 0:
                        break
                    if len(chunk) > remaining:
                        chunk = chunk.iloc[:remaining]
                if chunk.empty:
                    continue
                ticks = build_ticks(chunk, instrument_id)
                catalog.write_data(ticks, skip_disjoint_check=True)
                rows_seen += len(chunk)
                ticks_written += len(ticks)
                if progress:
                    print(
                        f"  chunk {idx} rows={len(chunk):,} total_rows={rows_seen:,}",
                        flush=True,
                    )

    return rows_seen, ticks_written


def build_ticks(df: pd.DataFrame, instrument_id) -> list[TradeTick]:
    ticks: list[TradeTick] = []
    for row in df.itertuples(index=False):
        timestamp_ns = binance_timestamp_to_ns(int(row.timestamp))
        aggressor = AggressorSide.SELLER if bool(row.buyer_maker) else AggressorSide.BUYER
        ticks.append(
            TradeTick(
                instrument_id=instrument_id,
                price=Price(float(row.price), 2),
                size=Quantity(float(row.quantity), 8),
                aggressor_side=aggressor,
                trade_id=TradeId(str(row.trade_id)),
                ts_event=timestamp_ns,
                ts_init=timestamp_ns,
            )
        )
    return ticks


def binance_timestamp_to_ns(raw: int) -> int:
    if raw >= 10_000_000_000_000:
        return raw * 1_000
    return raw * 1_000_000


def render_chart(points: list[TradeTick], html_path: Path, sample_points: int) -> Path:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    if not points:
        raise SystemExit("No trade ticks available for charting")

    sampled = points[:: max(len(points) // sample_points, 1)]
    times = pd.to_datetime([int(t.ts_event) for t in sampled], utc=True)
    prices = [float(t.price) for t in sampled]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="lines",
            line=dict(width=1.2, color="#0f766e"),
            name="BTCUSDT trade price",
        )
    )
    fig.update_layout(
        title="NautilusTrader BTCUSDT TradeTick Catalog Demo",
        xaxis_title="Time UTC",
        yaxis_title="Price",
        template="plotly_white",
        height=720,
        margin=dict(l=50, r=30, t=60, b=40),
    )
    fig.write_html(str(html_path), include_plotlyjs=True, full_html=True)
    return html_path


if __name__ == "__main__":
    raise SystemExit(main())
