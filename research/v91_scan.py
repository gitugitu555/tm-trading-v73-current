"""Univariate and alpha-family discovery helpers for V9.1."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from statistics import mean, median
from typing import Any, Callable

import numpy as np
import pandas as pd


def monthly_rank_ic(feature_frame: pd.DataFrame, labels: pd.DataFrame, feature: str, label: str) -> dict[str, Any]:
    if "month" in feature_frame.columns:
        months = feature_frame["month"]
    elif "end_ts_ns" in feature_frame.columns:
        months = pd.to_datetime(feature_frame["end_ts_ns"], utc=True).dt.strftime("%Y-%m")
    else:
        months = pd.Series(["unknown"] * len(feature_frame))
    frame = pd.concat([pd.DataFrame({"month": months, feature: feature_frame[feature]}).reset_index(drop=True), labels[[label]].reset_index(drop=True)], axis=1)
    grouped = frame.groupby("month", sort=True)
    values = []
    for _, group in grouped:
        if group[feature].nunique() < 2 or group[label].nunique() < 2:
            continue
        ic = group[feature].corr(group[label], method="spearman")
        if not np.isnan(ic):
            values.append(float(ic))
    if not values:
        return {"feature": feature, "label": label, "mean_ic": 0.0, "median_ic": 0.0, "positive_month_rate": 0.0, "trade_count": len(frame)}
    deciles = _decile_expectancy(frame[feature].to_numpy(dtype=float), frame[label].to_numpy(dtype=float))
    return {
        "feature": feature,
        "label": label,
        "mean_ic": float(mean(values)),
        "median_ic": float(median(values)),
        "ic_t_stat": float(np.mean(values) / (np.std(values, ddof=1) / np.sqrt(len(values)))) if len(values) > 1 and np.std(values, ddof=1) else 0.0,
        "positive_month_rate": float(sum(value > 0 for value in values) / len(values)),
        "best_decile_expectancy": float(max(deciles.values())) if deciles else 0.0,
        "worst_decile_expectancy": float(min(deciles.values())) if deciles else 0.0,
        "monotonicity_score": float(_monotonicity(deciles)),
        "monthly_stability": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "trade_count": int(len(frame)),
        "deciles": deciles,
    }


def discover_features(feature_frame: pd.DataFrame, labels: pd.DataFrame, label_columns: list[str]) -> dict[str, Any]:
    excluded = {
        "start_ts_ns",
        "end_ts_ns",
        "bar_start_ts_ns",
        "bar_end_ts_ns",
        "bar_id",
        "ticks",
    }
    numeric_features = [
        column for column in feature_frame.columns
        if column not in excluded
        and column not in {"month", "day", "year", "session_label", "volatility_regime", "volume_regime", "bar_duration_regime"}
        and pd.api.types.is_numeric_dtype(feature_frame[column])
    ]
    reports = []
    for feature in numeric_features:
        for label in label_columns:
            if label not in labels.columns:
                continue
            report = monthly_rank_ic(feature_frame, labels, feature, label)
            reports.append(report)
    return {"reports": reports, "count": len(reports)}


def _decile_expectancy(feature: np.ndarray, label: np.ndarray) -> dict[str, float]:
    valid = np.isfinite(feature) & np.isfinite(label)
    feature = feature[valid]
    label = label[valid]
    if len(feature) < 10:
        return {}
    bins = pd.qcut(pd.Series(feature), 10, duplicates="drop")
    result: dict[str, float] = {}
    for bucket, index in bins.groupby(bins).groups.items():
        result[str(bucket)] = float(np.mean(label[index]))
    return result


def _monotonicity(deciles: dict[str, float]) -> float:
    if len(deciles) < 2:
        return 0.0
    values = list(deciles.values())
    diffs = np.diff(values)
    return float(np.mean(np.sign(diffs) >= 0))


def build_candidate_signals(feature_frame: pd.DataFrame, rule: Callable[[pd.DataFrame], pd.Series], *, side: int) -> list[dict[str, Any]]:
    mask = pd.Series(rule(feature_frame), index=feature_frame.index).fillna(False).astype(bool)
    candidates = []
    for idx, row in feature_frame.loc[mask].iterrows():
        candidates.append(
            {
                "signal_id": f"V91_{idx}_{side}",
                "bar_id": int(idx),
                "signal_ts_ns": int(row["end_ts_ns"]),
                "side": "long" if side > 0 else "short",
                "side_int": side,
                "entry_reference_price": float(row["close"]),
                "signal_strength": float(row.get("continuation_setup_score", row.get("absorption_score", 0.0))),
                "old_divergence_score": float(row.get("old_divergence_score", 0.0)),
                "old_divergence_signal": int(row.get("old_divergence_signal", 0)),
                "old_signal_strength": float(row.get("old_signal_strength", 0.0)),
                "old_signal_side": int(row.get("old_signal_side", 0)),
                "old_policy_expected_value_if_available": float(row.get("old_policy_expected_value_if_available", 0.0)),
                "feature_snapshot": row.to_dict(),
            }
        )
    return candidates
