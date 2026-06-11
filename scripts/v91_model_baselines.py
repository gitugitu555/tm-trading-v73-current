#!/usr/bin/env python3
"""Chronological model baselines for V9.1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v91_models import chronological_split, decision_stump, logistic_regression_baseline, model_metrics, predict_logistic


def main() -> int:
    features = pq.read_table(ROOT / "results/v91_alpha_discovery/features/feature_ledger.parquet").to_pandas()
    labels = pq.read_table(ROOT / "results/v91_alpha_discovery/labels/labels.parquet").to_pandas()
    frame = features.join(labels[["future_return_24", "net_profitable_after_8bps_roundtrip"]])
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["future_return_24"])
    train, test = chronological_split(frame, 0.8)
    excluded = {"future_return_24", "net_profitable_after_8bps_roundtrip", "start_ts_ns", "end_ts_ns", "bar_start_ts_ns", "bar_end_ts_ns", "bar_id", "ticks", "month", "day", "year", "session_label", "volatility_regime", "volume_regime", "bar_duration_regime"}
    numeric_features = [column for column in train.columns if column not in excluded and np.issubdtype(train[column].dtype, np.number)]
    feature = numeric_features[0]
    x_train = train[[feature]].to_numpy(dtype=float)
    y_train = (train["future_return_24"] > 0).astype(int).to_numpy()
    x_test = test[[feature]].to_numpy(dtype=float)
    y_test = (test["future_return_24"] > 0).astype(int).to_numpy()
    weights = logistic_regression_baseline(x_train, y_train)
    train_prob = predict_logistic(weights, x_train)
    test_prob = predict_logistic(weights, x_test)
    stump = decision_stump(x_train[:, 0], y_train)
    report = {
        "feature": feature,
        "logistic_train": model_metrics(train_prob, y_train),
        "logistic_test": model_metrics(test_prob, y_test),
        "decision_tree": stump,
        "train_count": len(train),
        "test_count": len(test),
        "walk_forward_note": "chronological split only",
    }
    out = ROOT / "results/v91_alpha_discovery/model_baselines"
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_baselines.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v91_alpha_discovery/05_model_baselines.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Model Baselines\n\n"
        "The baseline models are evaluated with a chronological train/test split and converted into trade-relevance only after calibration.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
