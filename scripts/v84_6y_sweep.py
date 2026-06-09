#!/usr/bin/env python3
"""Run a multi-process parameter sweep over the 6-year history to find the absolute best settings."""

from __future__ import annotations

import itertools
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prime.performance import sharpe_ratio
from storage.hot_path import hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()


def get_archives(dest: Path) -> list[Path]:
    all_a = sorted(a for a in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in a.name)
    months_with_daily = {
        m.group(1)
        for a in all_a
        if (m := re.match(r"BTCUSDT-aggTrades-(\d{4}-\d{2})-\d{2}\.zip", a.name))
    }
    out: list[Path] = []
    for a in all_a:
        if re.match(r"BTCUSDT-aggTrades-\d{4}-\d{2}\.zip$", a.name):
            month_key = a.name.replace("BTCUSDT-aggTrades-", "").replace(".zip", "")
            if month_key in months_with_daily:
                continue
        out.append(a)
    return out


def run_single_backtest(
    archive: str,
    lookback: int,
    exit_bars: int,
    target_pct: float,
    stop_pct: float,
    dest: Path,
) -> list[dict]:
    # Runs chunk_b_backtest_cached.py and returns the list of trade dicts
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmp:
        trades_out = Path(tmp) / "trades.jsonl"
        cmd = [
            sys.executable,
            str(ROOT / "scripts/chunk_b_backtest_cached.py"),
            "--dest", str(dest),
            "--archive", archive,
            "--threshold-btc", "300.0",
            "--signal-mode", "divergence",
            "--divergence-type", "volume_bar_cvd",
            "--divergence-lookback-bars", str(lookback),
            "--exit-after-volume-bars", str(exit_bars),
            "--no-use-time-exit",
            "--stop-pct", str(stop_pct),
            "--target-pct", str(target_pct),
            "--no-use-cvd-reversal-confirm",
            "--starting-equity", "100000.0",
            "--base-position-pct", "0.01",
            "--entry-lag-bars", "0",
            "--trades-out", str(trades_out),
            "--manifest-jsonl", "/dev/null",
        ]
        cmd.append("--scale-target-by-strength")
        
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": f"/home/tokio/tm-trading-research:{ROOT}"},
        )
        if not trades_out.is_file():
            return []
        
        trades = []
        with trades_out.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    trades.append(json.loads(line))
        return trades


def evaluate_config(params: tuple[int, int, float, float], archives_list: list[Path], dest: Path) -> dict:
    lookback, exit_bars, target_pct, stop_pct = params
    all_trades = []
    for archive in archives_list:
        trades = run_single_backtest(
            archive.name,
            lookback,
            exit_bars,
            target_pct,
            stop_pct,
            dest,
        )
        all_trades.extend(trades)
        
    if not all_trades:
        return {
            "params": params,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "ending_equity": 0.0,
            "trades": 0,
        }
        
    all_trades.sort(key=lambda t: t.get("entry_ts_ns", 0))
    
    # Calculate sequential compounding
    current_equity = 100000.0
    for t in all_trades:
        pos_size = current_equity * 0.01
        trade_return = t.get("return_pct", 0.0)
        pnl = pos_size * trade_return
        current_equity += pnl
        t["pnl"] = pnl
        
    returns = [t["return_pct"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]
    sharpe = sharpe_ratio(returns)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / len(all_trades)
    
    return {
        "params": {
            "lookback": lookback,
            "exit_bars": exit_bars,
            "target_pct": target_pct,
            "stop_pct": stop_pct,
        },
        "win_rate": round(win_rate, 4),
        "sharpe": round(sharpe, 4),
        "ending_equity": round(current_equity, 2),
        "trades": len(all_trades),
    }


def main() -> int:
    dest = DEFAULT_DEST
    all_archives = get_archives(dest)
    
    # Grid search parameters
    lookbacks = [30]
    exit_bars = [20, 24]
    targets = [0.0045, 0.005, 0.0055]
    stops = [0.025, 0.03, 0.035]
    
    param_grid = list(itertools.product(lookbacks, exit_bars, targets, stops))
    print(f"6y Sweep: Running {len(param_grid)} configs in parallel using ProcessPoolExecutor...", flush=True)
    
    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(evaluate_config, params, all_archives, dest): params for params in param_grid}
        done = 0
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            results.append(res)
            print(
                f"[{done}/{len(param_grid)}] Done: "
                f"LB={res['params']['lookback']} Exit={res['params']['exit_bars']} "
                f"T={res['params']['target_pct']:.4f} S={res['params']['stop_pct']:.4f} -> "
                f"WR={res['win_rate']:.2%} Sharpe={res['sharpe']:.4f} Equity={res['ending_equity']:.2f}",
                flush=True,
            )
            
    # Sort by Sharpe
    results.sort(key=lambda r: -r["sharpe"])
    print("\n=== TOP 5 PARAMETER CONFIGURATIONS BY SHARPE ===")
    for idx, r in enumerate(results[:5]):
        p = r["params"]
        print(
            f"{idx+1}. LB={p['lookback']} Exit={p['exit_bars']} Target={p['target_pct']:.4f} Stop={p['stop_pct']:.4f} | "
            f"Sharpe: {r['sharpe']:.4f} | Win Rate: {r['win_rate']:.2%} | Ending Equity: {r['ending_equity']:.2f} | Trades: {r['trades']}"
        )
        
    Path("results/v84_6y_sweep_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
