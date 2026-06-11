#!/usr/bin/env python3
"""Run a staged V8.8 TPSL/MFE policy matrix over one immutable ledger."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl, write_jsonl
from research.v88_policy_replay import replay_policy


def main() -> int:
    signals = load_jsonl(ROOT / "results/v88_tpsl_replay/signal_ledgers/immutable_signal_ledger.jsonl")
    paths = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v88_tpsl_replay/trade_paths/trade_paths.jsonl")}
    policies = []
    for target, stop, bar_exit in itertools.product((0.0025, 0.005, 0.0075), (0.005, 0.01, 0.03), (8, 16, 24, 48, 72)):
        policies.append({"name": f"fixed_t{target}_s{stop}_b{bar_exit}", "target_pct": target, "stop_pct": stop, "bar_exit": bar_exit})
    for trigger, lock in itertools.product((0.001, 0.002, 0.0035, 0.005), (0.0, 0.0005, 0.001)):
        policies.append({"name": f"be_{trigger}_{lock}", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "breakeven_trigger_mfe_pct": trigger, "breakeven_lock_pct": lock})
    for start, giveback in itertools.product((0.002, 0.0035, 0.005), (0.25, 0.5, 0.66)):
        policies.append({"name": f"trail_{start}_{giveback}", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": start, "trail_giveback_pct": giveback})
    results = {}
    out = ROOT / "results/v88_tpsl_replay/policy_replays"
    out.mkdir(parents=True, exist_ok=True)
    for policy in policies:
        result = replay_policy(signals, paths, policy, occupancy_mode="independent")
        results[policy["name"]] = {"policy": policy, **{key: value for key, value in result.items() if key != "trades"}}
    ranked = sorted(results, key=lambda name: results[name]["summary"]["net_expectancy"], reverse=True)
    payload = {"tested_policy_count": len(results), "ranked": ranked, "results": results}
    (out / "policy_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if ranked:
        best = replay_policy(signals, paths, results[ranked[0]]["policy"], occupancy_mode="independent")
        write_jsonl(out / "best_policy_trades.jsonl", best["trades"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
