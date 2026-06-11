"""Timestamp-safe label generation from the verified catalog."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from research.v89_volume_bar_builder import load_verified_catalog


def build_labels(catalog_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    bars = load_verified_catalog(catalog_path)
    frame = pd.DataFrame([asdict(bar) for bar in bars])
    for horizon in (8, 16, 24, 48):
        frame[f"future_return_{horizon}_bars"] = _future_return(frame["close"], horizon)
    frame["max_favorable_excursion_24"] = _future_excursion(frame["high"], frame["close"], 24, favorable=True)
    frame["max_adverse_excursion_24"] = _future_excursion(frame["low"], frame["close"], 24, favorable=False)
    for target, stop in ((0.002, 0.002), (0.0035, 0.0035), (0.005, 0.005), (0.0075, 0.0075)):
        frame[f"triple_barrier_{target:g}_{stop:g}_24"] = _triple_barrier(frame["close"], frame["high"], frame["low"], target, stop, 24)
    frame["mfe_reaches_0.2pct_before_mae_0.2pct"] = (_future_excursion(frame["high"], frame["close"], 24, favorable=True) >= 0.002) & (_future_excursion(frame["low"], frame["close"], 24, favorable=False) < 0.002)
    frame["mfe_reaches_0.35pct_before_mae_0.2pct"] = (_future_excursion(frame["high"], frame["close"], 24, favorable=True) >= 0.0035) & (_future_excursion(frame["low"], frame["close"], 24, favorable=False) < 0.002)
    frame["trend_continuation_label"] = frame["future_return_24_bars"] > 0
    frame["mean_reversion_label"] = frame["future_return_24_bars"] < 0
    manifest = {"catalog_path": str(catalog_path), "row_count": len(frame), "label_count": len(frame.columns), "created_at": pd.Timestamp.utcnow().isoformat()}
    return frame, manifest


def write_labels(frame: pd.DataFrame, manifest: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame), output_dir / "labels.parquet", compression="zstd")
    (output_dir / "label_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _future_return(close: pd.Series, horizon: int) -> pd.Series:
    return close.shift(-horizon) / close - 1.0


def _future_excursion(series: pd.Series, close: pd.Series, horizon: int, *, favorable: bool) -> pd.Series:
    values = close.to_numpy(dtype=float)
    extremes = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for idx in range(len(values)):
        window = slice(idx + 1, min(len(values), idx + 1 + horizon))
        if window.start >= window.stop:
            continue
        if favorable:
            out[idx] = np.max(extremes[window] / values[idx] - 1.0)
        else:
            out[idx] = np.max(values[idx] / extremes[window] - 1.0)
    return pd.Series(out).fillna(0.0)


def _triple_barrier(close: pd.Series, high: pd.Series, low: pd.Series, target: float, stop: float, horizon: int) -> pd.Series:
    closes = close.to_numpy(dtype=float)
    highs = high.to_numpy(dtype=float)
    lows = low.to_numpy(dtype=float)
    labels = np.zeros(len(closes), dtype=int)
    for idx in range(len(closes)):
        base = closes[idx]
        end = min(len(closes), idx + 1 + horizon)
        label = 0
        for j in range(idx + 1, end):
            if highs[j] >= base * (1 + target):
                label = 1
                break
            if lows[j] <= base * (1 - stop):
                label = -1
                break
        labels[idx] = label
    return pd.Series(labels)
