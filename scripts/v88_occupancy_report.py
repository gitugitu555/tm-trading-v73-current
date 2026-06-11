#!/usr/bin/env python3
"""Compare occupancy policies over the same immutable signals and TPSL policy."""

from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v88_policy_replay import replay_policy

def main() -> int:
    signals = load_jsonl(ROOT / "results/v88_tpsl_replay/signal_ledgers/immutable_signal_ledger.jsonl")
    paths = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v88_tpsl_replay/trade_paths/trade_paths.jsonl")}
    all_results = json.loads((ROOT / "results/v88_tpsl_replay/policy_replays/policy_summary.json").read_text())
    best = all_results["results"][all_results["ranked"][0]]["policy"]
    report = {"independent": replay_policy(signals, paths, best, occupancy_mode="independent")}
    for cap in (1, 2, 3, 5, 10):
        report[f"capped_{cap}"] = replay_policy(signals, paths, best, occupancy_mode="capped", max_concurrent=cap)
    for value in report.values(): value.pop("trades", None)
    out = ROOT / "results/v88_tpsl_replay/occupancy"; out.mkdir(parents=True, exist_ok=True)
    (out / "occupancy_modes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
