#!/usr/bin/env python3
import subprocess
import json
import os
import sys
from pathlib import Path

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

def run_backtest(use_extreme: bool) -> dict:
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    
    for archive in ARCHIVES_6M:
        cmd = [
            str(PYTHON),
            str(SCRIPT),
            "--archive", archive,
            "--threshold-btc", "300.0",
            "--signal-mode", "divergence",
            "--divergence-type", "volume_bar_cvd",
            "--divergence-lookback-bars", "40",
            "--exit-after-volume-bars", "16",
            "--stop-pct", "0.03",
            "--target-pct", "0.004",
            "--no-use-time-exit",
            "--no-use-regime-gate-volume-bar",
            "--no-use-footprint-confluence",
            "--no-use-auction-state-gate",
            "--no-use-vwap-gate",
            "--no-use-cvd-reversal-confirm",
            "--use-stress-regime",
            "--use-session-extreme-gate" if use_extreme else "--no-use-session-extreme-gate",
            "--manifest-jsonl", "/dev/null"
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"/home/tokio/tm-trading-research:{ROOT}"
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
        
        text = proc.stdout.strip()
        if not text:
            print(f"Error for {archive}: {proc.stderr}")
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
        "use_session_extreme_gate": use_extreme,
        "total_trades": total_trades,
        "win_rate": agg_wr,
        "total_pnl": total_pnl
    }

def main():
    print("Testing session extreme gate on 6-month window...")
    res_with = run_backtest(use_extreme=True)
    res_without = run_backtest(use_extreme=False)
    
    print("\nRESULTS:")
    print(f"With extreme gate (Default):")
    print(f"  Trades: {res_with['total_trades']} | Win Rate: {res_with['win_rate']:.4f} | PnL: {res_with['total_pnl']:.2f}")
    print(f"Without extreme gate:")
    print(f"  Trades: {res_without['total_trades']} | Win Rate: {res_without['win_rate']:.4f} | PnL: {res_without['total_pnl']:.2f}")

if __name__ == "__main__":
    main()
