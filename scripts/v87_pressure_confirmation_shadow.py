#!/usr/bin/env python3
"""Shadow-test observable trade-flow pressure agreement at partial signals."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v87_execution import execution_summary, timing_ledger


def main() -> int:
    events = [row for row in load_jsonl(ROOT / "results/v87_execution_rescue/signal_observability/partial_signal_events.jsonl") if row.get("partial_fraction") == 0.5 and row.get("partial_signal")]
    groups = {"agrees": [], "disagrees": [], "neutral": []}
    for row in events:
        pressure = float(row.get("partial_delta", 0.0))
        agreement = int(row["partial_side"]) * pressure
        groups["agrees" if agreement > 0 else "disagrees" if agreement < 0 else "neutral"].append(row)
    report = {
        "scope": "aggTrades signed-flow proxy; not order-book OFI/MLOFI",
        "groups": {name: execution_summary(timing_ledger(rows, timing_field="partial_price", side_field="partial_side")) for name, rows in groups.items()},
    }
    out = ROOT / "results/v87_execution_rescue/pressure_confirmation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pressure_shadow.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/06_pressure_confirmation_shadow.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Pressure Confirmation Shadow\n\nThe current report uses signed trade-flow delta only. True OFI, queue imbalance, spread, and microprice require aligned L2 data and remain shadow-unavailable.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
