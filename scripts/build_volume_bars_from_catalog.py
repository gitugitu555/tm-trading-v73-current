#!/usr/bin/env python3
"""Build Tier-1 immutable VolumeBar parquets from Nautilus ParquetDataCatalog (Tier 0).

This is the foundation script for fast iteration:
- Ingest raw ticks into catalog ONCE (see scripts/nautilus_btc_catalog_demo.py).
- For each bar threshold (e.g. 300, 200), run this ONCE to materialize VolumeBars.
- All subsequent work (CVD divergence signals D4/D5, HTF filters, lookback sweeps,
  regime classification over bars, permission logic, backtests using bar history)
  becomes pure functions over the loaded bars (Tier 3). No more ZIP streaming,
  no re-sampling on param changes for bar size.

Parity contract:
- Bars written here are constructed via the exact same VolumeBarSampler used
  everywhere (prime/volume_bars.py).
- When the catalog contains the ticks that were previously processed from a
  given ZIP via iter_binance_research_ticks, the emitted VolumeBar sequence
  will be identical (same start/end, OHLC, volumes, delta, cumulative_delta, ticks).
- Pure signal functions (prime/volume_bar_cvd.py) are unaffected and will
  produce identical outputs given the bar history.

Usage (example for the two primary thresholds):
  .venv/bin/python scripts/build_volume_bars_from_catalog.py \
    --catalog-path data/nautilus/catalogs/btcusdt_trade_ticks_6y \
    --threshold-btc 300 200 \
    --progress

Outputs (default):
  data/nautilus/volume_bars/<catalog_name>.threshold-300.v2.parquet
  ... plus sidecar build info if extended.

The parquet schema mirrors the bar fields + provenance columns so that
prime/volume_bar_cache.load_catalog_bars and prime/bar_provider can consume it.

Supports windowed queries to avoid loading billions of ticks in RAM.
Resumable / idempotent: skips existing outputs unless --force.

After build, v73 diagnostics and backtesters can load via:
  from prime.bar_provider import get_bars
  bars = get_bars(300)
  # then use with volume_bar_cvd_signal(bars, lookback_bars=..., ...)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Ensure project root on path when run as script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.persistence.catalog import ParquetDataCatalog
except Exception as exc:  # pragma: no cover - builder requires Nautilus
    print("NautilusTrader is required for catalog access:", exc, file=sys.stderr)
    sys.exit(2)

from prime.volume_bars import VolumeBar, VolumeBarSampler
from prime.volume_bar_cache import (
    write_catalog_bars,  # direct writer (cache_dir, catalog_path, threshold, rows_seen, bars)
)
from prime.bar_provider import DEFAULT_BAR_CACHE_DIR


DEFAULT_CATALOG = Path("data/nautilus/catalogs/btcusdt_trade_ticks_6y")
DEFAULT_OUT_DIR = DEFAULT_BAR_CACHE_DIR


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--catalog-path",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Path to the ParquetDataCatalog containing trade_tick data",
    )
    p.add_argument(
        "--threshold-btc",
        type=float,
        nargs="+",
        default=[300.0, 200.0],
        help="Volume bar thresholds (BTC units). Build all in one pass.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for the consolidated threshold parquets",
    )
    p.add_argument(
        "--instrument",
        default="BTCUSDT.BINANCE",
        help="Instrument ID in the catalog",
    )
    p.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Query window size in days for streaming (memory safe)",
    )
    p.add_argument(
        "--start",
        help="Optional ISO start (inclusive) to limit build window",
    )
    p.add_argument(
        "--end",
        help="Optional ISO end (inclusive) to limit build window",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Safety cap on ticks processed (for testing)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if output files already exist",
    )
    p.add_argument(
        "--progress",
        action="store_true",
        help="Print periodic progress (every N ticks)",
    )
    p.add_argument(
        "--progress-every",
        type=int,
        default=5_000_000,
        help="Tick count between progress prints",
    )
    return p.parse_args()


def parse_datetime_ns(value: str | None) -> int | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


def iter_catalog_ticks(
    *,
    catalog: ParquetDataCatalog,
    instrument_id: str,
    start_ns: int | None,
    end_ns: int | None,
    window_days: int,
    max_rows: int | None,
) -> Iterable[TradeTick]:
    """Windowed streaming iterator over TradeTicks. Mirrors the proven pattern
    in scripts/nautilus_chunkb_backtest.py to keep memory bounded.
    Yields ticks in strict time order.
    """
    emitted = 0
    if window_days <= 0:
        window_days = 30

    if start_ns is None:
        first = catalog.query_first_timestamp(TradeTick, instrument_id)
        start_ns = int(first.value) if first is not None else 0
    if end_ns is None:
        last = catalog.query_last_timestamp(TradeTick, instrument_id)
        end_ns = int(last.value) if last is not None else 0

    if start_ns > end_ns:
        return

    window_ns = window_days * 24 * 60 * 60 * 1_000_000_000
    cursor = start_ns
    while cursor <= end_ns:
        upper = min(cursor + window_ns - 1, end_ns)
        # query returns list (or iterable) of TradeTick for the slice
        batch = catalog.query(
            TradeTick,
            identifiers=[instrument_id],
            start=cursor,
            end=upper,
        )
        for tick in batch:
            yield tick
            emitted += 1
            if max_rows is not None and emitted >= max_rows:
                return
        cursor = upper + 1


def build_bars(
    catalog: ParquetDataCatalog,
    thresholds: list[float],
    instrument_id: str,
    start_ns: int | None,
    end_ns: int | None,
    window_days: int,
    max_rows: int | None,
    progress: bool = False,
    progress_every: int = 5_000_000,
) -> tuple[dict[float, list[VolumeBar]], int]:
    """Single pass over catalog ticks, update all samplers, emit bars per threshold.

    Returns (bars_by_threshold, total_ticks_seen)
    """
    samplers = {float(t): VolumeBarSampler(float(t)) for t in thresholds}
    bars_by_threshold: dict[float, list[VolumeBar]] = {float(t): [] for t in thresholds}
    rows_seen = 0
    last_progress = 0

    for tick in iter_catalog_ticks(
        catalog=catalog,
        instrument_id=instrument_id,
        start_ns=start_ns,
        end_ns=end_ns,
        window_days=window_days,
        max_rows=max_rows,
    ):
        rows_seen += 1
        for thresh, sampler in samplers.items():
            bar = sampler.update(tick)
            if bar is not None:
                bars_by_threshold[thresh].append(bar)

        if progress and (rows_seen - last_progress) >= progress_every:
            print(f"  ... processed {rows_seen:,} ticks from catalog")
            last_progress = rows_seen

    if progress:
        print(f"  Done. Total ticks processed: {rows_seen:,}")
        for t in sorted(bars_by_threshold):
            print(f"    threshold {t}: {len(bars_by_threshold[t]):,} bars")

    return bars_by_threshold, rows_seen


def write_sidecar_info(
    out_dir: Path,
    catalog_path: Path,
    thresholds: list[float],
    rows_seen: int,
    bars_by_threshold: dict[float, list[VolumeBar]],
    started_at: str,
) -> Path:
    """Write a small JSON build manifest next to the bars for provenance."""
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {
        "build_tool": "scripts/build_volume_bars_from_catalog.py",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "source_catalog": str(catalog_path.resolve()),
        "catalog_name": catalog_path.name,
        "instrument": "BTCUSDT.BINANCE",
        "rows_seen": rows_seen,
        "thresholds": sorted([float(t) for t in thresholds]),
        "bar_counts": {str(float(t)): len(bars_by_threshold.get(float(t), [])) for t in thresholds},
        "cache_version": 2,
        "volume_bar_sampler": "prime.volume_bars.VolumeBarSampler",
    }
    info_path = out_dir / f"{catalog_path.name}.build-info.json"
    info_path.write_text(json.dumps(info, indent=2, sort_keys=True), encoding="utf-8")
    return info_path


def main() -> int:
    args = parse_args()
    catalog_path = args.catalog_path.resolve()
    if not catalog_path.exists():
        print(f"ERROR: catalog not found: {catalog_path}", file=sys.stderr)
        return 2

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    thresholds = sorted(set(float(t) for t in args.threshold_btc))
    if not thresholds:
        print("No thresholds specified", file=sys.stderr)
        return 1

    start_ns = parse_datetime_ns(args.start)
    end_ns = parse_datetime_ns(args.end)

    print(f"Opening catalog: {catalog_path}")
    catalog = ParquetDataCatalog(str(catalog_path))

    # Pre-check existing to support idempotency
    to_build = []
    for t in thresholds:
        p = out_dir / f"{catalog_path.name}.threshold-{int(t) if t.is_integer() else str(t).replace('.', 'p')}.v2.parquet"
        # The actual path is computed inside persist via catalog_cache_path, but we approximate
        # for skip check. Use the provider-style name.
        if p.exists() and not args.force:
            print(f"  Exists (skip): {p.name} for threshold {t} (use --force to rebuild)")
        else:
            to_build.append(t)

    if not to_build and not args.force:
        print("All requested thresholds already present. Nothing to do.")
        return 0

    print(f"Building bars for thresholds: {to_build} (force={args.force})")
    started = datetime.now(timezone.utc).isoformat()

    bars_by_threshold, rows_seen = build_bars(
        catalog=catalog,
        thresholds=to_build if not args.force else thresholds,
        instrument_id=args.instrument,
        start_ns=start_ns,
        end_ns=end_ns,
        window_days=args.window_days,
        max_rows=args.max_rows,
        progress=args.progress,
        progress_every=args.progress_every,
    )

    # Persist using the shared writer (ensures format compatible with load_catalog_bars / provider)
    written = []
    for t in (to_build if not args.force else thresholds):
        bars = bars_by_threshold.get(t, [])
        out_path = write_catalog_bars(
            out_dir,
            catalog_path,
            t,
            rows_seen,
            bars,
        )
        if out_path:
            written.append(out_path)
            print(f"  Wrote {len(bars):,} bars for threshold {t} -> {out_path.name}")
        else:
            print(f"  WARNING: failed to write for threshold {t}", file=sys.stderr)

    info_path = write_sidecar_info(
        out_dir=out_dir,
        catalog_path=catalog_path,
        thresholds=thresholds,
        rows_seen=rows_seen,
        bars_by_threshold=bars_by_threshold,
        started_at=started,
    )
    print(f"Build info: {info_path}")

    # Quick sanity: load back via provider and compare counts
    try:
        from prime.bar_provider import VolumeBarProvider

        prov = VolumeBarProvider(cache_dir=out_dir, catalog_path=catalog_path)
        for t in thresholds:
            loaded = prov.load(t)
            expected = len(bars_by_threshold.get(t, []))
            if len(loaded) != expected:
                print(f"  SANITY WARNING: roundtrip count mismatch for {t}: {len(loaded)} vs {expected}")
            else:
                print(f"  Roundtrip OK for {t}: {len(loaded)} bars")
    except Exception as e:
        print(f"  (roundtrip sanity skipped: {e})")

    print("Build complete. Future sweeps over signals using these bars are now O(bars) pure python.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
