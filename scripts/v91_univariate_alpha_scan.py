#!/usr/bin/env python3
"""Run univariate and bucket scans over the V9.1 feature/label ledgers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v91_scan import discover_features


def main() -> int:
    features = pq.read_table(ROOT / "results/v91_alpha_discovery/features/feature_ledger.parquet").to_pandas()
    labels = pq.read_table(ROOT / "results/v91_alpha_discovery/labels/labels.parquet").to_pandas()
    label_columns = [
        "future_return_24",
        "net_profitable_after_4bps_roundtrip",
        "net_profitable_after_8bps_roundtrip",
        "touch_target_0.35_before_stop_0.2",
        "clean_trade_path_score",
    ]
    report = discover_features(features, labels, label_columns)
    out = ROOT / "results/v91_alpha_discovery/univariate_scan"
    out.mkdir(parents=True, exist_ok=True)
    (out / "univariate_scan.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v91_alpha_discovery/03_univariate_bucket_scan.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Univariate Bucket Scan\n\n"
        "The univariate scan evaluates rank IC, decile expectancy, and stability across the verified feature and label ledgers.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

