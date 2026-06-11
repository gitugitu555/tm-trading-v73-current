#!/usr/bin/env python3
"""Create expectancy, exit-reason, and MFE/MAE diagnostics from trade JSONL."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import grouped_expectancy, load_jsonl, normalize_trade, summarize_trades


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trade_files", nargs="*", type=Path)
    ns = parser.parse_args()
    files = ns.trade_files or sorted((ROOT / "results/v86_recovery/trades").glob("*.jsonl"))
    for path in files:
        label = path.stem
        rows = [normalize_trade(row, strategy_label=label) for row in load_jsonl(path)]
        diagnostics = ROOT / "results/v86_recovery/diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        expectancy = {
            "overall": summarize_trades(rows),
            "by_exit_reason": grouped_expectancy(rows, "exit_reason"),
            "by_side": grouped_expectancy(rows, "side"),
            "data_limitations": ["Counterfactual later-target fields are null unless emitted by the runner."],
        }
        (diagnostics / f"{label}_expectancy.json").write_text(json.dumps(expectancy, indent=2, sort_keys=True), encoding="utf-8")
        with (diagnostics / f"{label}_exit_reason_breakdown.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["exit_reason", "trades", "win_rate", "net_pnl", "expectancy", "profit_factor"])
            for reason, values in expectancy["by_exit_reason"].items():
                writer.writerow([reason, values["trade_count"], values["win_rate"], values["net_pnl"], values["expectancy_per_trade"], values["profit_factor"]])
        with (diagnostics / f"{label}_mfe_mae.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["exit_reason", "mfe_pct", "mae_pct", "pnl_net"])
            for row in rows:
                writer.writerow([row.get("exit_reason"), row["mfe_pct"], row["mae_pct"], row["pnl_net"]])
        doc = ROOT / "docs/v86_recovery" / f"{label}_diagnostic.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(f"# {label} Trade-Path Diagnostic\n\n```json\n{json.dumps(expectancy['overall'], indent=2)}\n```\n\nCounterfactual target-after-profile-exit analysis requires bar-path fields from a fresh V8.6 run.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
