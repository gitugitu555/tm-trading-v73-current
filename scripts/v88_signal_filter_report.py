#!/usr/bin/env python3
"""Evaluate simple immutable-ledger filters with blocked-trade accounting."""

from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v88_signal_filters import filter_value

def main() -> int:
    signals = load_jsonl(ROOT / "results/v88_tpsl_replay/signal_ledgers/immutable_signal_ledger.jsonl")
    trades = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v88_tpsl_replay/policy_replays/best_policy_trades.jsonl")}
    report = {}
    for value in (.25, .5, .75):
        report[f"strength_ge_{value}"] = filter_value(signals, trades, lambda s, v=value: float(s["signal_strength"]) >= v)
    report["cvd_slope_agrees"] = filter_value(signals, trades, lambda s: int(s["side_int"]) * float(s["cvd_slope"]) > 0)
    report["cvd_accel_agrees"] = filter_value(signals, trades, lambda s: int(s["side_int"]) * float(s["cvd_accel"]) > 0)
    out = ROOT / "results/v88_tpsl_replay/filters"; out.mkdir(parents=True, exist_ok=True)
    (out / "filter_value.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
