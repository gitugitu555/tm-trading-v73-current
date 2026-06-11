#!/usr/bin/env python3
"""Evaluate observable early-entry candidates from partial-bar signal events."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v87_execution import execution_summary, timing_ledger


def main() -> int:
    events = load_jsonl(ROOT / "results/v87_execution_rescue/signal_observability/partial_signal_events.jsonl")
    rules = {
        "rule_a_50pct_partial_divergence": [row for row in events if row["partial_fraction"] == 0.5 and row["partial_signal"]],
        "rule_b_70pct_partial_divergence": [row for row in events if row["partial_fraction"] == 0.7 and row["partial_signal"]],
        "rule_c_partial_plus_trade_flow_confirmation": [row for row in events if row["partial_fraction"] == 0.5 and row["partial_signal"] and row["partial_side"] * row["partial_delta"] > 0],
    }
    report = {
        "scope": "signal-horizon early-entry diagnostic",
        "rules": {},
        "unsupported": {
            "rule_d_microprice_ofi_queue_confirmation": "requires L2 data",
            "rule_f_maker_first_entry": "requires quote and queue data",
        },
    }
    for name, rows in rules.items():
        one_x = execution_summary(timing_ledger(rows, timing_field="partial_price", side_field="partial_side"))
        two_x = execution_summary(timing_ledger(rows, timing_field="partial_price", fee_bps_per_side=10, slippage_bps_per_side=2, side_field="partial_side"))
        report["rules"][name] = {"cost_1x": one_x, "cost_2x": two_x}
    out = ROOT / "results/v87_execution_rescue/early_entry"
    out.mkdir(parents=True, exist_ok=True)
    (out / "early_entry_candidates.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/03_early_entry_candidate_rules.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Early Entry Candidate Rules\n\nResults: `results/v87_execution_rescue/early_entry/early_entry_candidates.json`.\n\nTrade-flow confirmation is an aggTrades proxy, not OFI/MLOFI from an order book. Maker-first and microprice rules remain unavailable until L2 is aligned to signals.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
