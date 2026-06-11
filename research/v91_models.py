"""Simple chronological predictive models for V9.1."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


def chronological_split(frame: pd.DataFrame, train_fraction: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(frame) * train_fraction)
    return frame.iloc[:cut].copy(), frame.iloc[cut:].copy()


def logistic_regression_baseline(x: np.ndarray, y: np.ndarray, *, steps: int = 400, lr: float = 0.1) -> np.ndarray:
    x = np.column_stack([np.ones(len(x)), x])
    weights = np.zeros(x.shape[1])
    y = y.astype(float)
    for _ in range(steps):
        scores = np.clip(x @ weights, -60, 60)
        probs = 1.0 / (1.0 + np.exp(-scores))
        grad = x.T @ (probs - y) / len(y)
        weights -= lr * grad
    return weights


def predict_logistic(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    x = np.column_stack([np.ones(len(x)), x])
    return 1.0 / (1.0 + np.exp(-np.clip(x @ weights, -60, 60)))


def decision_stump(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    best = {"threshold": 0.0, "direction": 1, "score": -math.inf}
    for threshold in np.quantile(x, np.linspace(0.1, 0.9, 17)):
        for direction in (1, -1):
            pred = ((x - threshold) * direction > 0).astype(int)
            score = float((pred == y).mean())
            if score > best["score"]:
                best = {"threshold": float(threshold), "direction": direction, "score": score}
    return best


def model_metrics(prob: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    pred = (prob > 0.5).astype(int)
    tp = float(((pred == 1) & (y == 1)).sum())
    fp = float(((pred == 1) & (y == 0)).sum())
    tn = float(((pred == 0) & (y == 0)).sum())
    fn = float(((pred == 0) & (y == 1)).sum())
    return {
        "accuracy": float((tp + tn) / max(tp + tn + fp + fn, 1.0)),
        "precision": float(tp / max(tp + fp, 1.0)),
        "recall": float(tp / max(tp + fn, 1.0)),
        "brier": float(np.mean((prob - y) ** 2)),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }
