#!/usr/bin/env python3
"""Diagnose BAR_EXIT, PROFILE_HARD_STOP, and STOP loss concentration."""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl, normalize_trade, summarize_trades


def main() -> int:
    paths = sorted((ROOT / "results/v86_recovery/trades").glob("*.jsonl"))
    report = {}
    for path in paths:
        rows = [normalize_trade(row) for row in load_jsonl(path)]
        reasons = defaultdict(list)
        for row in rows:
            if row.get("exit_reason") in {"BAR_EXIT", "PROFILE_HARD_STOP", "STOP"}:
                reasons[row["exit_reason"]].append(row)
        if not reasons:
            continue
        report[path.stem] = {}
        for reason, trades in reasons.items():
            report[path.stem][reason] = {
                **summarize_trades(trades),
                "avg_mae": statistics.mean(float(row["mae_pct"]) for row in trades),
                "avg_mfe": statistics.mean(float(row["mfe_pct"]) for row in trades),
                "ever_positive_mfe_pct": sum(float(row["mfe_pct"]) > 0 for row in trades) / len(trades),
            }
    out = ROOT / "results/v87_execution_rescue/exit_loss_repair"
    out.mkdir(parents=True, exist_ok=True)
    (out / "exit_loss_diagnostics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/05_exit_loss_repair.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Exit Loss Repair\n\nHistorical-ledger diagnostics: `results/v87_execution_rescue/exit_loss_repair/exit_loss_diagnostics.json`.\n\nCounterfactual hold/stop variants require fresh path replay; MAE/MFE alone cannot establish stop recovery after exit.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
