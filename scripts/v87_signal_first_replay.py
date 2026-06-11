#!/usr/bin/env python3
"""Build an immutable final-signal ledger before applying execution timing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl, write_jsonl
from research.v87_execution import execution_summary, timing_ledger


def main() -> int:
    events_path = ROOT / "results/v87_execution_rescue/signal_observability/partial_signal_events.jsonl"
    events = [
        row for row in load_jsonl(events_path)
        if row.get("final_signal") and float(row.get("partial_fraction", 0)) == 1.0
    ]
    signals = {str(row["signal_id"]): row for row in events}
    immutable = [signals[key] for key in sorted(signals)]
    out = ROOT / "results/v87_execution_rescue/signal_first"
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "immutable_signal_ledger.jsonl", immutable)
    report = {
        "signal_count": len(immutable),
        "opportunity_set_fixed": True,
        "timings": {
            field: execution_summary(timing_ledger(immutable, timing_field=field))
            for field in ("lag0_close", "lag1_open", "lag1_close", "lag2_open")
        },
        "limitation": "Current exits use a fixed 24-volume-bar signal horizon. TPSL and capital-allocation replay must consume this same ledger next.",
    }
    (out / "fixed_signal_timing_comparison.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
