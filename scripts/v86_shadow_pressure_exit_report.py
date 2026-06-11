#!/usr/bin/env python3
"""Compare raw, CVD-confirmed, and pressure-confirmed profile exit shadows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.v86_recovery import load_jsonl, summarize_trades


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trade_file", type=Path)
    ns = parser.parse_args()
    rows = load_jsonl(ns.trade_file)
    result = {}
    for field in ("profile_exit_signal_raw", "profile_exit_signal_cvd_confirmed", "profile_exit_signal_pressure_confirmed"):
        selected = [row for row in rows if row.get(field)]
        result[field] = summarize_trades(selected)
    output = ROOT / "results/v86_recovery/diagnostics" / f"{ns.trade_file.stem}_pressure_exit_shadow.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
