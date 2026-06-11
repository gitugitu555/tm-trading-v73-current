#!/usr/bin/env python3
"""Audit whether lag-mode comparisons use the same underlying signal stream."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    trade_dir = ROOT / "results/v86_recovery/trades"
    lag0 = load(trade_dir / "v85_apples_legacy.jsonl")
    lag1 = load(trade_dir / "v85_apples_lag_only.jsonl")
    by0 = {str(row["signal_id"]): row for row in lag0}
    by1 = {str(row["signal_id"]): row for row in lag1}
    common = sorted(set(by0) & set(by1))
    entry_moves = [
        (float(by1[signal]["entry_price"]) - float(by0[signal]["entry_price"])) / float(by0[signal]["entry_price"])
        for signal in common
        if float(by0[signal]["entry_price"])
    ]
    report = {
        "lag0_trades": len(lag0),
        "lag1_trades": len(lag1),
        "common_signal_ids": len(common),
        "lag0_only_signal_ids": len(set(by0) - set(by1)),
        "lag1_only_signal_ids": len(set(by1) - set(by0)),
        "common_signal_retention_vs_lag0": len(common) / len(lag0) if lag0 else 0.0,
        "common_signal_lag0_net_pnl": sum(float(by0[signal]["pnl_net"]) for signal in common),
        "common_signal_lag1_net_pnl": sum(float(by1[signal]["pnl_net"]) for signal in common),
        "common_signal_avg_entry_move_pct": sum(entry_moves) / len(entry_moves) if entry_moves else 0.0,
        "common_signal_max_abs_entry_move_pct": max(map(abs, entry_moves)) if entry_moves else 0.0,
        "interpretation": "Lag mode changes the selected signal/trade path; this is not a fixed-signal execution-price comparison.",
    }
    out = ROOT / "results/v87_execution_rescue/runner_semantics"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lag_mode_signal_stream_audit.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
