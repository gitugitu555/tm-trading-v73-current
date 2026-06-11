"""Cost-aware labels for V9.1 alpha discovery."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from research.v89_volume_bar_builder import load_verified_catalog


def build_alpha_labels(catalog_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    bars = load_verified_catalog(catalog_path)
    frame = pd.DataFrame([asdict(bar) for bar in bars])
    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    for horizon in (8, 16, 24, 48):
        frame[f"future_return_{horizon}"] = _future_return(close, horizon)
        frame[f"mfe_{horizon}"] = _future_mfe(close, high, horizon)
        frame[f"mae_{horizon}"] = _future_mae(close, low, horizon)
    for horizon in (8, 16, 24):
        frame[f"sign_future_return_{horizon}"] = np.sign(frame[f"future_return_{horizon}"]).astype(int)
    touch_specs = {
        "touch_target_0.2_before_stop_0.2": (0.002, 0.002, 24),
        "touch_target_0.35_before_stop_0.2": (0.0035, 0.002, 24),
        "touch_target_0.5_before_stop_0.25": (0.005, 0.0025, 24),
        "touch_target_0.75_before_stop_0.35": (0.0075, 0.0035, 48),
    }
    for name, (target, stop, horizon) in touch_specs.items():
        frame[name] = _first_touch(close, high, low, target, stop, horizon)
    cost_specs = {
        "net_profitable_after_4bps_roundtrip": 0.0004,
        "net_profitable_after_8bps_roundtrip": 0.0008,
        "net_profitable_after_12bps_roundtrip": 0.0012,
        "net_profitable_after_20bps_roundtrip": 0.0020,
    }
    for name, cost in cost_specs.items():
        frame[name] = (frame["future_return_24"] - cost > 0).astype(int)
    frame["mfe_large_enough_to_pay_costs"] = (frame["mfe_24"] >= 0.0008).astype(int)
    frame["mae_small_enough_for_tight_stop"] = (frame["mae_24"] <= 0.0010).astype(int)
    frame["mfe_to_mae_ratio"] = _safe_ratio(frame["mfe_24"], frame["mae_24"])
    frame["clean_trade_path_score"] = frame["mfe_24"] - frame["mae_24"]
    manifest = {
        "catalog_path": str(catalog_path),
        "row_count": len(frame),
        "label_count": len(frame.columns),
        "cost_grid_bps_roundtrip": [4, 8, 12, 20],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label_hash": _hash_frame(frame),
    }
    return frame, manifest


def write_alpha_labels(frame: pd.DataFrame, manifest: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame), output_dir / "labels.parquet", compression="zstd")
    (output_dir / "label_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _future_return(close: pd.Series, horizon: int) -> pd.Series:
    return ((close.shift(-horizon) / close) - 1.0).fillna(0.0)


def _future_mfe(close: pd.Series, high: pd.Series, horizon: int) -> pd.Series:
    out = np.zeros(len(close), dtype=float)
    close_arr = close.to_numpy(dtype=float)
    high_arr = high.to_numpy(dtype=float)
    for idx in range(len(close_arr)):
        end = min(len(close_arr), idx + horizon + 1)
        if idx + 1 >= end:
            continue
        out[idx] = np.max(high_arr[idx + 1 : end] / close_arr[idx] - 1.0)
    return pd.Series(out)


def _future_mae(close: pd.Series, low: pd.Series, horizon: int) -> pd.Series:
    out = np.zeros(len(close), dtype=float)
    close_arr = close.to_numpy(dtype=float)
    low_arr = low.to_numpy(dtype=float)
    for idx in range(len(close_arr)):
        end = min(len(close_arr), idx + horizon + 1)
        if idx + 1 >= end:
            continue
        out[idx] = np.max(1.0 - low_arr[idx + 1 : end] / close_arr[idx])
    return pd.Series(out)


def _first_touch(close: pd.Series, high: pd.Series, low: pd.Series, target: float, stop: float, horizon: int) -> pd.Series:
    close_arr = close.to_numpy(dtype=float)
    high_arr = high.to_numpy(dtype=float)
    low_arr = low.to_numpy(dtype=float)
    labels = np.zeros(len(close_arr), dtype=int)
    for idx in range(len(close_arr)):
        end = min(len(close_arr), idx + horizon + 1)
        if idx + 1 >= end:
            continue
        label = 0
        for j in range(idx + 1, end):
            if high_arr[j] >= close_arr[idx] * (1 + target):
                label = 1
                break
            if low_arr[j] <= close_arr[idx] * (1 - stop):
                label = -1
                break
        labels[idx] = label
    return pd.Series(labels)


def _safe_ratio(numer: pd.Series, denom: pd.Series) -> pd.Series:
    return (numer / denom.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _hash_frame(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(frame.to_json(orient="records", date_unit="ns").encode("utf-8"))
    return digest.hexdigest()

