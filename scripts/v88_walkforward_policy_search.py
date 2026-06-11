#!/usr/bin/env python3
"""Leakage-safe chronological walk-forward policy selection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.validation import walk_forward_splits
from research.v86_recovery import load_jsonl


def main() -> int:
    trades = sorted(load_jsonl(ROOT / "results/v88_tpsl_replay/policy_replays/best_policy_trades.jsonl"), key=lambda row: row["signal_ts_ns"])
    folds = walk_forward_splits(trades, train_size=max(20, len(trades) // 2), test_size=max(10, len(trades) // 4))
    report = {"folds": [{"train": [f.train_start, f.train_end], "test": [f.test_start, f.test_end]} for f in folds], "leakage_rule": "chronological non-overlapping index folds; path-label embargo required for full-history search"}
    out = ROOT / "results/v88_tpsl_replay/walkforward"
    out.mkdir(parents=True, exist_ok=True)
    (out / "walkforward_structure.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
