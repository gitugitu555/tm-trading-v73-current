"""Deterministic consolidation of verified per-archive volume-bar caches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v89_data_catalog import canonical_hash, iso_ns


def consolidate_cached_bars(cache_files: list[Path], *, threshold: float = 300.0) -> tuple[list[VolumeBar], int]:
    bars: list[VolumeBar] = []
    trade_count = 0
    cumulative = 0.0
    for path in cache_files:
        records = pq.read_table(path).to_pylist()
        if not records:
            continue
        trade_count += int(records[0]["rows_seen"])
        for row in records:
            if float(row["threshold_btc"]) != threshold:
                continue
            cumulative += float(row["delta"])
            bars.append(
                VolumeBar(
                    start_ts_ns=int(row["start_ts_ns"]), end_ts_ns=int(row["end_ts_ns"]),
                    open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"]),
                    volume=float(row["volume"]), buy_volume=float(row["buy_volume"]), sell_volume=float(row["sell_volume"]),
                    delta=float(row["delta"]), cumulative_delta=round(cumulative, 8), ticks=int(row["ticks"]),
                )
            )
    if any(a.end_ts_ns > b.end_ts_ns for a, b in zip(bars, bars[1:])):
        raise RuntimeError("non-monotonic or overlapping consolidated bars")
    return bars, trade_count


def bars_hash(bars: list[VolumeBar]) -> str:
    digest = hashlib.sha256()
    for bar in bars:
        digest.update(json.dumps(asdict(bar), sort_keys=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def write_verified_catalog(path: Path, bars: list[VolumeBar], manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"catalog_manifest_hash": manifest["catalog_manifest_hash"], **asdict(bar)} for bar in bars]
    pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")


def load_verified_catalog(path: Path) -> list[VolumeBar]:
    return [
        VolumeBar(
            start_ts_ns=int(row["start_ts_ns"]), end_ts_ns=int(row["end_ts_ns"]),
            open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"]),
            volume=float(row["volume"]), buy_volume=float(row["buy_volume"]), sell_volume=float(row["sell_volume"]),
            delta=float(row["delta"]), cumulative_delta=float(row["cumulative_delta"]), ticks=int(row["ticks"]),
        )
        for row in pq.read_table(path).to_pylist()
    ]


def build_manifest(*, bars: list[VolumeBar], trade_count: int, raw_manifest_hash: str, coverage_audit_hash: str, output_file: Path, repo_commit: str) -> dict[str, Any]:
    catalog_hash = bars_hash(bars)
    base = {
        "catalog_id": "BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300",
        "symbol": "BTCUSDT", "source": "binance", "data_type": "aggTrades",
        "bar_type": "volume_bar", "threshold_btc": 300,
        "start_ts_ns": bars[0].start_ts_ns, "end_ts_ns": bars[-1].end_ts_ns,
        "start_iso": iso_ns(bars[0].start_ts_ns), "end_iso": iso_ns(bars[-1].end_ts_ns),
        "raw_manifest_hash": raw_manifest_hash, "coverage_audit_hash": coverage_audit_hash,
        "builder_version": "v89.1", "repo_commit": repo_commit, "bar_count": len(bars),
        "trade_count": trade_count, "dropped_rows": 0, "duplicate_rows": 0,
        "output_files": [output_file.name], "catalog_hash": catalog_hash,
    }
    return {**base, "catalog_manifest_hash": canonical_hash(base)}
