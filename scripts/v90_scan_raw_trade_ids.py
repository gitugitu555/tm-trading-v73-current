#!/usr/bin/env python3
"""Stream raw aggTrades archives and checkpoint duplicate scans."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v90_duplicate_scan import scan_archives
from storage.hot_path import hot_btcusdt_aggtrades_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-archives", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=False, help="Resume from checkpoint state if present.")
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "results/v90_validation_closure/duplicate_scan/checkpoint.json")
    args = parser.parse_args()
    raw_dir = hot_btcusdt_aggtrades_dir()
    archives = sorted(a for a in raw_dir.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)
    if args.max_archives is not None:
        archives = archives[: args.max_archives]
    result = scan_archives(archives, checkpoint_path=args.checkpoint)
    if args.max_archives is not None and args.max_archives < len(sorted(a for a in raw_dir.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)):
        result["scan_complete"] = False
    out = ROOT / "results/v90_validation_closure/duplicate_scan"
    out.mkdir(parents=True, exist_ok=True)
    (out / "final_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v90_validation_closure/02_raw_trade_duplicate_scan.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Raw Trade Duplicate Scan\n\n"
        "The scanner is resumable and checkpointed. Run it against the raw BTCUSDT aggTrades archives to complete the audit.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
