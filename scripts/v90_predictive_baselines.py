#!/usr/bin/env python3
"""Run simple predictive baselines over the V9.0 feature and label ledgers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v90_predictive_baselines import predictive_baselines


def main() -> int:
    report = predictive_baselines(
        ROOT / "results/v90_alpha_rebuild/feature_ledger/feature_ledger.parquet",
        ROOT / "results/v90_alpha_rebuild/labels/labels.parquet",
    )
    out = ROOT / "results/v90_alpha_rebuild/predictive_baselines"
    out.mkdir(parents=True, exist_ok=True)
    (out / "predictive_baselines.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v90_alpha_rebuild/04_predictive_baselines.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Predictive Baselines\n\n"
        "The baseline artifact records feature IC, threshold search, logistic, and tree metrics.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
