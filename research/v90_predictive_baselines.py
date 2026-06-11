"""Simple predictive baselines over the V9.0 feature and label ledgers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def predictive_baselines(feature_path: Path, label_path: Path, target_col: str = "future_return_24_bars") -> dict[str, Any]:
    features = pq.read_table(feature_path).to_pandas()
    labels = pq.read_table(label_path).to_pandas()
    frame = pd.concat([features.reset_index(drop=True), labels[[target_col]].reset_index(drop=True)], axis=1)
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=[target_col])
    y = (frame[target_col] > 0).astype(float).to_numpy()
    numeric = frame.select_dtypes(include=["number"]).drop(columns=[target_col], errors="ignore")
    ic = {column: float(numeric[column].corr(frame[target_col])) for column in numeric.columns if numeric[column].std() and not math.isnan(numeric[column].corr(frame[target_col]))}
    ranked = sorted(ic.items(), key=lambda item: abs(item[1]), reverse=True)
    best_feature = ranked[0][0] if ranked else None
    if best_feature is None:
        return {"feature_ic": ic, "ranked": ranked, "best_feature": None}
    threshold_report = _threshold_search(frame[best_feature].to_numpy(dtype=float), y)
    logistic = _logistic_baseline(frame[best_feature].to_numpy(dtype=float), y)
    tree = _decision_stump(frame[best_feature].to_numpy(dtype=float), y)
    return {
        "feature_ic": ic,
        "ranked": ranked,
        "best_feature": best_feature,
        "threshold_search": threshold_report,
        "logistic_regression": logistic,
        "decision_tree": tree,
        "walk_forward_note": "feature-level out-of-sample split required for promotion",
    }


def _threshold_search(feature: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    best = {"threshold": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0}
    for threshold in np.quantile(feature[~np.isnan(feature)], np.linspace(0.1, 0.9, 17)):
        pred = (feature > threshold).astype(float)
        best = max(best, _binary_metrics(pred, y), key=lambda row: row["accuracy"])
    return best


def _logistic_baseline(feature: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    x = np.column_stack([np.ones(len(feature)), np.nan_to_num(feature, nan=0.0)])
    weights = np.zeros(x.shape[1])
    for _ in range(500):
        scores = x @ weights
        probs = 1.0 / (1.0 + np.exp(-scores))
        grad = x.T @ (probs - y) / len(y)
        weights -= 0.1 * grad
    pred = (1.0 / (1.0 + np.exp(-(x @ weights))) > 0.5).astype(float)
    metrics = _binary_metrics(pred, y)
    metrics["weights"] = weights.tolist()
    return metrics


def _decision_stump(feature: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    best = {"threshold": 0.0, "direction": 1, "accuracy": 0.0}
    quantiles = np.quantile(feature[~np.isnan(feature)], np.linspace(0.05, 0.95, 19))
    for threshold in quantiles:
        for direction in (1, -1):
            pred = ((feature - threshold) * direction > 0).astype(float)
            metrics = _binary_metrics(pred, y)
            if metrics["accuracy"] > best["accuracy"]:
                best = {"threshold": float(threshold), "direction": direction, **metrics}
    return best


def _binary_metrics(pred: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    pred = pred.astype(float)
    tp = float(((pred == 1) & (y == 1)).sum())
    fp = float(((pred == 1) & (y == 0)).sum())
    tn = float(((pred == 0) & (y == 0)).sum())
    fn = float(((pred == 0) & (y == 1)).sum())
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1.0)
    precision = tp / max(tp + fp, 1.0)
    recall = tp / max(tp + fn, 1.0)
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "tp": tp, "fp": fp, "tn": tn, "fn": fn}

