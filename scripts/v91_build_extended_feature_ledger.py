#!/usr/bin/env python3
"""Build the extended V9.1 feature ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v91_features import build_extended_feature_ledger, write_extended_feature_ledger


def main() -> int:
    catalog_path = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    frame, manifest = build_extended_feature_ledger(catalog_path)
    out = ROOT / "results/v91_alpha_discovery/features"
    write_extended_feature_ledger(frame, manifest, out)
    doc = ROOT / "docs/v91_alpha_discovery/01_extended_feature_ledger.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Extended Feature Ledger\n\n"
        "The extended feature ledger adds absorption, continuation, and regime features on top of the verified catalog.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

