#!/usr/bin/env python3
"""Measure signal-horizon alpha decay across observable entry timings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl
from research.v87_execution import execution_summary, timing_ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, default=ROOT / "results/v87_execution_rescue/signal_observability/partial_signal_events.jsonl")
    ns = parser.parse_args()
    all_events = load_jsonl(ns.events)
    events = [row for row in all_events if row.get("final_signal")]
    timings = {
        "lag0_close": ("lag0_close", None),
        "lag0_midbar_if_signal_confirmed_25pct_bar": ("partial_price", 0.25),
        "lag0_midbar_if_signal_confirmed_50pct_bar": ("partial_price", 0.5),
        "lag0_midbar_if_signal_confirmed_75pct_bar": ("partial_price", 0.75),
        "lag1_open": ("lag1_open", None),
        "lag1_close": ("lag1_close", None),
        "lag2_open": ("lag2_open", None),
    }
    report = {
        "scope": "signal-horizon diagnostic; not a full strategy backtest",
        "timings": {},
        "unavailable_timing_modes": {
            "lag0_next_tick_after_signal_observable": "requires next-tick capture after first partial signal; not approximated",
        },
    }
    out = ROOT / "results/v87_execution_rescue/alpha_decay"
    out.mkdir(parents=True, exist_ok=True)
    for label, (field, fraction) in timings.items():
        selected = events
        if fraction is not None:
            selected = [row for row in all_events if row["partial_fraction"] == fraction and row["partial_signal"]]
        elif field == "lag0_close":
            selected = [row for row in events if row["partial_fraction"] == 1.0]
        else:
            selected = [row for row in events if row["partial_fraction"] == 1.0]
        ledger = timing_ledger(selected, timing_field=field, side_field="partial_side" if fraction is not None else "final_side")
        report["timings"][label] = {
            **execution_summary(ledger),
            "by_side": {
                side: execution_summary([row for row in ledger if row["side"] == side_value])
                for side, side_value in (("long", 1), ("short", -1))
            },
        }
    (out / "alpha_decay_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v87_execution_rescue/01_alpha_decay_report.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# V8.7 Alpha Decay Report\n\nResults are stored in `results/v87_execution_rescue/alpha_decay/alpha_decay_summary.json`.\n\nCurrent implementation is an honest signal-horizon diagnostic. Full strategy-state timing comparisons require entry timing support inside the backtester.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
