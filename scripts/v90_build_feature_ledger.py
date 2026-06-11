#!/usr/bin/env python3
"""Build the per-bar feature ledger from the verified V8.9 catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v90_feature_ledger import build_feature_ledger, write_feature_ledger


def main() -> int:
    catalog_path = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    frame, manifest = build_feature_ledger(catalog_path)
    out = ROOT / "results/v90_alpha_rebuild/feature_ledger"
    write_feature_ledger(frame, manifest, out)
    doc = ROOT / "docs/v90_alpha_rebuild/02_shadow_feature_ledger.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Shadow Feature Ledger\n\n"
        "The feature ledger is aligned to the verified catalog and written as a deterministic parquet artifact.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
