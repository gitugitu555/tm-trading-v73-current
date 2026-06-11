#!/usr/bin/env python3
"""Evaluate lag-1 price-decay filters with blocked-winner/loss accounting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v87_execution import decay_filter_value, timing_ledger


def main() -> int:
    events = [row for row in load_jsonl(ROOT / "results/v87_execution_rescue/signal_observability/partial_signal_events.jsonl") if row.get("final_signal") and row.get("partial_fraction") == 1.0]
    ledger = timing_ledger(events, timing_field="lag1_open")
    for trade, event in zip(ledger, events):
        trade["lag0_close"] = event["lag0_close"]
        trade["lag1_open"] = event["lag1_open"]
    report = {
        str(threshold): decay_filter_value(ledger, max_move_pct=threshold)
        for threshold in (0.0005, 0.0010, 0.0015)
    }
    out = ROOT / "results/v87_execution_rescue/entry_decay"
    out.mkdir(parents=True, exist_ok=True)
    (out / "price_decay_filters.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/04_entry_price_decay_filters.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Entry Price Decay Filters\n\nResults: `results/v87_execution_rescue/entry_decay/price_decay_filters.json`.\n\nFilters are ranked by net blocked-trade value, not win rate.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
