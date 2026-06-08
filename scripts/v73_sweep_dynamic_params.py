#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import itertools
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
SCRIPT = ROOT / "scripts/chunk_b_backtest_cached.py"
ARCHIVES_6M = [
    "BTCUSDT-aggTrades-2024-12.zip",
    "BTCUSDT-aggTrades-2025-01.zip",
    "BTCUSDT-aggTrades-2025-02.zip",
    "BTCUSDT-aggTrades-2025-03.zip",
    "BTCUSDT-aggTrades-2025-04.zip",
    "BTCUSDT-aggTrades-2025-05.zip",
]

def run_config(base_target: float, exit_bars: int, lookback: int) -> dict:
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    
    # We run archives in parallel or sequentially. Sequentially is fine since Parquet caching is active.
    for archive in ARCHIVES_6M:
        cmd = [
            str(PYTHON),
            str(SCRIPT),
            "--archive", archive,
            "--threshold-btc", "300.0",
            "--signal-mode", "divergence",
            "--divergence-type", "volume_bar_cvd",
            "--divergence-lookback-bars", str(lookback),
            "--exit-after-volume-bars", str(exit_bars),
            "--stop-pct", "0.03",
            "--target-pct", str(base_target),
            "--no-use-time-exit",
            "--no-use-regime-gate-volume-bar",
            "--no-use-footprint-confluence",
            "--no-use-auction-state-gate",
            "--no-use-vwap-gate",
            "--no-use-cvd-reversal-confirm",
            "--use-stress-regime",
            "--scale-target-by-strength",
            "--manifest-jsonl", "/dev/null"
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"/home/tokio/tm-trading-research:{ROOT}"
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
        
        text = proc.stdout.strip()
        if not text:
            continue
        start = text.find("{")
        if start >= 0:
            payload = json.loads(text[start:])
            rep = payload.get("report", {})
            trades = rep.get("trades", 0)
            wr = rep.get("win_rate", 0.0)
            wins = int(round(wr * trades))
            total_trades += trades
            total_wins += wins
            total_pnl += rep.get("total_pnl", 0.0)
            
    agg_wr = total_wins / total_trades if total_trades else 0.0
    return {
        "base_target": base_target,
        "exit_bars": exit_bars,
        "lookback": lookback,
        "total_trades": total_trades,
        "win_rate": agg_wr,
        "total_pnl": total_pnl
    }

def main():
    print("Sweeping dynamic parameter variations over the 6-month window...", flush=True)
    
    # Param space
    base_targets = [0.003, 0.004, 0.005, 0.006]
    exit_bars_list = [10, 16, 20, 24]
    lookbacks = [30, 40, 50, 60]
    
    param_combinations = list(itertools.product(base_targets, exit_bars_list, lookbacks))
    results = []
    
    # Run in parallel using a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(run_config, t, e, lb)
            for t, e, lb in param_combinations
        ]
        for idx, fut in enumerate(futures):
            res = fut.result()
            results.append(res)
            print(f"[{idx+1}/{len(param_combinations)}] BaseTarget: {res['base_target']:.4f} | Exits: {res['exit_bars']} | Lookback: {res['lookback']} | WR: {res['win_rate']:.4f} | PnL: {res['total_pnl']:.2f}", flush=True)
            
    # Sort and show top 10 by win rate & top 10 by PnL
    print("\n--- TOP 10 BY WIN RATE ---")
    top_wr = sorted(results, key=lambda x: x["win_rate"], reverse=True)[:10]
    for r in top_wr:
        print(f"Target: {r['base_target']} | Exits: {r['exit_bars']} | Lookback: {r['lookback']} | WR: {r['win_rate']:.4f} | PnL: {r['total_pnl']:.2f}")

    print("\n--- TOP 10 BY PNL ---")
    top_pnl = sorted(results, key=lambda x: x["total_pnl"], reverse=True)[:10]
    for r in top_pnl:
        print(f"Target: {r['base_target']} | Exits: {r['exit_bars']} | Lookback: {r['lookback']} | WR: {r['win_rate']:.4f} | PnL: {r['total_pnl']:.2f}")

if __name__ == "__main__":
    main()
