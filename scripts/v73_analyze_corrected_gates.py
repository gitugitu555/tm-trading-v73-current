#!/usr/bin/env python3
"""Run gates sweep and output full results for all configurations so we can see best of each target."""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from scripts.v73_sweep_corrected_gates_6m import SweepConfig, build_configs, _worker

ROOT = Path(__file__).resolve().parents[1]

def main():
    configs = build_configs()
    workers = int(os.environ.get("SWEEP_WORKERS", "16"))
    print(f"Analyzing gates sweep: {len(configs)} configs, workers={workers}", flush=True)
    
    cfg_dicts = [
        {
            "name": c.name,
            "target_pct": c.target_pct,
            "exit_bars": c.exit_bars,
            "lookback": c.lookback,
            "use_footprint": c.use_footprint,
            "footprint_require_stacked": c.footprint_require_stacked,
            "footprint_allow_neutral": c.footprint_allow_neutral,
            "use_auction": c.use_auction,
            "use_regime": c.use_regime,
            "use_vwap": c.use_vwap,
            "approve_only": c.approve_only,
            "extra": list(c.extra),
        }
        for c in configs
    ]
    
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, d): d["name"] for d in cfg_dicts}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            results.append(row)
            
    # Sort all results by win rate
    results.sort(key=lambda r: (-r.get("win_rate", 0.0), -r.get("total_pnl", 0.0)))
    
    # Save ALL results
    output_path = ROOT / "results/v73_sweep_corrected_gates_6m_all.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    
    # Group by target
    for target in [0.004, 0.005, 0.006]:
        target_results = [r for r in results if abs(r["config"]["target_pct"] - target) < 1e-5]
        print(f"\nTOP 5 FOR TARGET {target}:")
        for r in target_results[:5]:
            print(f"  Name: {r.get('name')} | WR: {r.get('win_rate')} | PnL: {r.get('total_pnl')} | Trades: {r.get('total_trades')}")

if __name__ == "__main__":
    main()
