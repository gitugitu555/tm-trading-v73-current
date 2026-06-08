"""Unified immutable bar provider for Tier 1 volume bars (from catalog).

Design goals:
- Tier 0 (raw ticks): Nautilus ParquetDataCatalog - ingest once.
- Tier 1 (volume bars): per-threshold consolidated parquets built once from catalog.
- Tier 2 (snapshots at bar close): optional future (footprint, session CVD etc).
- Tier 3: all signal, regime, permission, exit logic = pure functions over
  Sequence[VolumeBar] (see prime/volume_bar_cvd.py, divergence_side_at, etc).
  Zero tick reprocessing or re-sampling for lookback/gate/TP-SL/confluence sweeps.

This provider + the build script make future iterations (lookback, htf quantile,
D4 vs D5, regime gates, etc) cheap: load bars once (~ms), then pure python.

Parity: bars produced by build + loaded here are identical VolumeBar instances
to those emitted by VolumeBarSampler when fed the equivalent TradeTick stream.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from prime.volume_bars import VolumeBar
from prime.volume_bar_cache import (
    CATALOG_CACHE_VERSION,
    load_catalog_bars,
    write_catalog_bars,
    persist_catalog_bars as _persist_catalog_bars,
)


DEFAULT_BAR_CACHE_DIR = Path("data/nautilus/volume_bars")


class VolumeBarProvider:
    """Loads pre-built VolumeBar series for a threshold from Tier-1 cache.

    Prefers catalog-sourced consolidated caches (new immutable foundation).
    Future: can be extended with fallback to legacy per-archive volume_bar_cvd_cache
    aggregation or indicator_cache bar fields, for migration.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        catalog_path: Path | None = None,
    ) -> None:
        self.cache_dir = (cache_dir or DEFAULT_BAR_CACHE_DIR).resolve()
        self.catalog_path = catalog_path  # for provenance / validation

    def load(
        self,
        threshold: float,
        *,
        start_ns: int | None = None,
        end_ns: int | None = None,
    ) -> list[VolumeBar]:
        """Load bars for threshold. Optionally time-slice by bar.end_ts_ns.

        Returns [] on miss (caller can trigger build or fallback).
        """
        if self.catalog_path is None:
            # Try to infer from common layout if not provided at construction.
            # This keeps provider usable with defaults.
            cand = self._discover_default_catalog()
            if cand:
                self.catalog_path = cand

        bars = load_catalog_bars(self.cache_dir, self.catalog_path or Path("unknown"), threshold)
        if bars is None:
            return []

        if start_ns is not None or end_ns is not None:
            filtered = []
            for b in bars:
                if start_ns is not None and b.end_ts_ns < start_ns:
                    continue
                if end_ns is not None and b.end_ts_ns > end_ns:
                    continue
                filtered.append(b)
            return filtered
        return bars

    def available_thresholds(self) -> list[float]:
        """Best-effort scan of cache dir for known catalog-style bar files."""
        if not self.cache_dir.exists():
            return []
        threshs: set[float] = set()
        for p in self.cache_dir.glob("*.v*.parquet"):
            name = p.name
            # Expect patterns like ...threshold-300.v2.parquet or threshold-200p0...
            if "threshold-" in name:
                try:
                    part = name.split("threshold-")[1].split(".")[0]
                    if "p" in part:
                        t = float(part.replace("p", "."))
                    else:
                        t = float(part)
                    threshs.add(t)
                except Exception:
                    pass
        return sorted(threshs)

    def _discover_default_catalog(self) -> Path | None:
        # Common locations relative to typical workspace roots.
        candidates = [
            Path("data/nautilus/catalogs/btcusdt_trade_ticks_6y"),
            Path("/home/tokio/tm-trading-v73-current/data/nautilus/catalogs/btcusdt_trade_ticks_6y"),
            Path("/home/tokio/tm-trading-v555/data/nautilus/catalogs/btcusdt_trade_ticks_6y"),
        ]
        for c in candidates:
            if c.exists() and (c / "data").exists():
                return c.resolve()
        return None


def get_bars(
    threshold: float,
    *,
    cache_dir: Path | None = None,
    catalog_path: Path | None = None,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> list[VolumeBar]:
    """Convenience: load bars for a threshold via default provider."""
    prov = VolumeBarProvider(cache_dir=cache_dir, catalog_path=catalog_path)
    return prov.load(threshold, start_ns=start_ns, end_ns=end_ns)


# Re-export the writer for callers who want the low-level persist
persist_catalog_bars = _persist_catalog_bars
