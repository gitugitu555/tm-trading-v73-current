#!/usr/bin/env python3
"""Generate V8.6 robustness reports from canonical trade ledgers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl, robustness_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trade_files", nargs="*", type=Path)
    parser.add_argument("--n-trials", type=int, default=1)
    ns = parser.parse_args()
    files = ns.trade_files or sorted((ROOT / "results/v86_recovery/trades").glob("*.jsonl"))
    output = ROOT / "results/v86_recovery/robustness"
    output.mkdir(parents=True, exist_ok=True)
    index = {}
    for path in files:
        metrics = robustness_metrics(load_jsonl(path), n_trials=ns.n_trials)
        (output / f"{path.stem}.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
        index[path.stem] = metrics
    doc = ROOT / "docs/v86_recovery/05_robustness_report.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.6 Robustness Report\n\nRobustness results are stored per strategy under `results/v86_recovery/robustness/`.\n\nPromotion remains blocked until a candidate passes DSR, 2x cost sensitivity, year/regime stability, and purged validation.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
