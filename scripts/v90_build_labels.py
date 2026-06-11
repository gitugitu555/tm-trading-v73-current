#!/usr/bin/env python3
"""Build timestamp-safe labels from the verified V8.9 catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v90_labels import build_labels, write_labels


def main() -> int:
    catalog_path = ROOT / "results/v89_data_foundation/catalog/BTCUSDT_volume_bars_2020-05-22_2026-05-21_threshold300.parquet"
    frame, manifest = build_labels(catalog_path)
    out = ROOT / "results/v90_alpha_rebuild/labels"
    write_labels(frame, manifest, out)
    doc = ROOT / "docs/v90_alpha_rebuild/03_label_generation.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Label Generation\n\n"
        "Future-return and triple-barrier labels were generated from the verified catalog.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
