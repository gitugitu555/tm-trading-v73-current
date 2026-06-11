#!/usr/bin/env python3
"""Build the V9.1 cost-aware alpha labels."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v91_labels import build_alpha_labels, write_alpha_labels


def main() -> int:
    catalog_path = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    frame, manifest = build_alpha_labels(catalog_path)
    out = ROOT / "results/v91_alpha_discovery/labels"
    write_alpha_labels(frame, manifest, out)
    doc = ROOT / "docs/v91_alpha_discovery/02_label_design.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.1 Label Design\n\n"
        "The label set includes direction, excursion, first-touch, and cost-aware profitability targets.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

