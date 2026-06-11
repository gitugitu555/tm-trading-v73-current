#!/usr/bin/env python3
"""Document and evaluate execution models supported by available datasets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    report = {
        "supported_now": {
            "taker_at_observable_trade_tick": "partial-bar audit supplies observable trade price and timestamp",
            "lag1_open": "volume-bar cache supplies next bar open",
            "passive_pullback_price_condition": "can be tested as a price-touch diagnostic, not as guaranteed fill",
        },
        "unsupported_without_aligned_l2": {
            "maker_fill_probability": "requires bid/ask queue and cancellations",
            "spread_cost": "aggTrades has no quotes",
            "microprice": "requires top-of-book sizes",
            "queue_imbalance": "requires L2/L3",
            "latency_50ms_to_5s": "requires retaining next ticks after each observable signal",
        },
        "decision": "Do not fabricate maker fills or latency prices from bar closes.",
    }
    out = ROOT / "results/v87_execution_rescue/execution_simulation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "execution_model_availability.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/07_execution_simulation.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Execution Simulation\n\nNo maker-fill or quote-latency results are reported from trade-only aggTrades. See `results/v87_execution_rescue/execution_simulation/execution_model_availability.json`.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
