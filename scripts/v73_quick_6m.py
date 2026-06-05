#!/usr/bin/env python3
"""Quick 6m tests for high-priority research configs."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.v73_sweep_6m import ARCHIVES_6M, STOP_PCT, THRESHOLD, SweepConfig, run_config

PRIORITY = [
    SweepConfig("prio_scalp", target_pct=0.003, exit_bars=12, lookback=40),
    SweepConfig("prio_scalp_lb25", target_pct=0.003, exit_bars=12, lookback=25),
    SweepConfig("prio_bar12", target_pct=0.004, exit_bars=12, lookback=40),
    SweepConfig("prio_no_gates", regime_gate=False, footprint=False, auction_gate=False, target_pct=0.004, exit_bars=12),
    SweepConfig("prio_d5", extra=["--use-delta-rev-2-entry", "--htf-flat-quantile", "0.15"], lookback=25, target_pct=0.004, exit_bars=12),
    SweepConfig("prio_cvd_exit", extra=["--use-cvd-exit"], target_pct=0.004, exit_bars=12),
    SweepConfig("prio_bar_only", extra=["--no-use-tpsl"], exit_bars=12, lookback=40),
    SweepConfig("prio_regime_off", regime_gate=False, target_pct=0.004, exit_bars=12),
    SweepConfig("prio_foot_off", footprint=False, target_pct=0.004, exit_bars=12),
    SweepConfig(
        "prio_combo",
        extra=["--use-delta-rev-2-entry", "--htf-flat-quantile", "0.15", "--use-cvd-exit"],
        lookback=25,
        target_pct=0.003,
        exit_bars=12,
        footprint=False,
    ),
]

def main():
    rows = []
    for c in PRIORITY:
        r = run_config(c)
        rows.append(r)
        print(f"{c.name}: wr={r.get('win_rate')} trades={r.get('total_trades')} pnl={r.get('total_pnl')}")
    rows.sort(key=lambda x: -x.get("win_rate", 0))
    out = ROOT / "results/v73_quick_6m.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("BEST:", rows[0]["name"], rows[0]["win_rate"])

if __name__ == "__main__":
    main()