#!/usr/bin/env python3
"""Report capital paths without allowing sizing to hide negative expectancy."""

from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v88_capital_allocation import replay_capital

def main() -> int:
    trades = load_jsonl(ROOT / "results/v88_tpsl_replay/policy_replays/best_policy_trades.jsonl")
    report = {str(pct): replay_capital(trades, base_position_pct=pct) for pct in (.005, .01, .02, .05, .10, .25, .50)}
    report["drawdown_throttle_10pct"] = replay_capital(trades, base_position_pct=.10, drawdown_throttle=True)
    out = ROOT / "results/v88_tpsl_replay/capital"; out.mkdir(parents=True, exist_ok=True)
    (out / "capital_allocation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
