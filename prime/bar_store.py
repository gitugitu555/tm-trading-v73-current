"""Tier 1/2 bar store and provider.

Lightweight loader for pre-built volume bars produced by build_volume_bars.py (or future bar materializers).

Goal: allow backtests, diagnostics, and sweeps to consume bars + optional snapshots directly from disk (or catalog in future) without ever touching raw ticks for signal work.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from prime.volume_bars import VolumeBar


@dataclass(frozen=True)
class BarStoreConfig:
    cache_dir: Path = Path("results/volume_bars")
    threshold_btc: float = 300.0


def load_bars(
    cache_dir: Path,
    threshold_btc: float,
    archives: Sequence[str] | None = None,
) -> list[VolumeBar]:
    """Load VolumeBars for a threshold.

    Expects files named like bars.threshold-300.parquet (full) or per-archive files.
    For MVP we support a single combined or per-archive in the dir.
    """
    cache_dir = Path(cache_dir)
    candidates = [
        cache_dir / f"bars.threshold-{int(threshold_btc)}.parquet",
        cache_dir / f"volume_bars.threshold-{int(threshold_btc)}.parquet",
    ]

    df = None
    for c in candidates:
        if c.exists():
            df = pd.read_parquet(c)
            break

    if df is None:
        # Fallback: look for per-archive style if archives given (future)
        raise FileNotFoundError(f"No bar cache found for threshold {threshold_btc} in {cache_dir}")

    bars: list[VolumeBar] = []
    for row in df.itertuples():
        # Be tolerant of column names
        b = VolumeBar(
            start_ts_ns=int(getattr(row, "start_ts_ns", row[0] if hasattr(row, "__getitem__") else 0)),
            end_ts_ns=int(getattr(row, "end_ts_ns", 0)),
            open=float(getattr(row, "open", 0)),
            high=float(getattr(row, "high", 0)),
            low=float(getattr(row, "low", 0)),
            close=float(getattr(row, "close", 0)),
            volume=float(getattr(row, "volume", 0)),
            buy_volume=float(getattr(row, "buy_volume", 0)),
            sell_volume=float(getattr(row, "sell_volume", 0)),
            delta=float(getattr(row, "delta", 0)),
            cumulative_delta=float(getattr(row, "cumulative_delta", 0)),
            ticks=int(getattr(row, "ticks", 0)),
        )
        bars.append(b)

    if archives:
        # TODO: filter if per-archive metadata present
        pass

    return bars


def iter_bars_from_store(
    cache_dir: Path, threshold_btc: float, **kwargs
) -> Iterable[VolumeBar]:
    """Convenience iterator for backtesters."""
    for b in load_bars(cache_dir, threshold_btc, **kwargs):
        yield b


# Future: support loading + joining Tier 2 snapshots (footprint etc.) into enriched bars or separate dicts.
