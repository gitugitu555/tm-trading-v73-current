#!/usr/bin/env python3
"""Monthly walk-forward selection on the verified immutable replay set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v86_recovery import load_jsonl
from research.v90_walkforward import build_monthly_walkforward_report


def main() -> int:
    signals = load_jsonl(ROOT / "results/v89_data_foundation/verified_signal_ledger/immutable_signal_ledger.jsonl")
    paths = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v89_data_foundation/verified_trade_paths/trade_paths.jsonl")}
    report = build_monthly_walkforward_report(signals, paths)
    out = ROOT / "results/v90_validation_closure/monthly_walkforward"
    out.mkdir(parents=True, exist_ok=True)
    (out / "monthly_walkforward.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v90_validation_closure/03_monthly_walkforward.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Monthly Walk-Forward\n\n"
        "The walk-forward structure is implemented over the verified immutable ledger. The JSON artifact contains the fold summaries.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
