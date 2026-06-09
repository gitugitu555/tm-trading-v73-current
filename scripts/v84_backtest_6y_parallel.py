#!/usr/bin/env python3
"""V8.4 parallelized six-year backtest runner.

Runs the chunk backtests for all 132 archives in parallel using a ProcessPoolExecutor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prime.performance import deflated_sharpe_probability, kurtosis, sharpe_ratio, skewness
from research.promotion_summary import build_promotion_summary
from research.mae_mfe_exit_lab import MAEMFEExitLab
from research.trade_path_db import TradePathDatabase
from storage.hot_path import assert_nvme_archive, hot_btcusdt_aggtrades_dir

DEFAULT_DEST = hot_btcusdt_aggtrades_dir()
CACHE_DIR = ROOT / "results/indicator_cache"
DEFAULT_WORK_DIR = ROOT / "results/v84_backtest_6y_parallel_work"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    p.add_argument("--threshold-btc", type=float, default=300.0)
    p.add_argument("--divergence-lookback-bars", type=int, default=30)
    p.add_argument("--exit-after-volume-bars", type=int, default=24)
    p.add_argument("--stop-pct", type=float, default=0.03)
    p.add_argument("--target-pct", type=float, default=0.005)
    p.add_argument("--scale-target-by-strength", action="store_true", default=True)
    p.add_argument("--starting-equity", type=float, default=100000.0)
    p.add_argument("--base-position-pct", type=float, default=0.01)
    p.add_argument("--entry-lag-bars", type=int, default=0)
    p.add_argument("--workers", type=int, default=24)

    # Gates
    p.add_argument("--use-vpin-gate", action="store_true", default=False)
    p.add_argument("--use-market-profile-gate", action="store_true", default=False)
    p.add_argument("--use-anti-pattern-gate", action="store_true", default=False)
    p.add_argument("--use-risk-state-gate", action="store_true", default=False)
    p.add_argument("--use-auction-state-gate", action="store_true", default=False)
    p.add_argument("--use-regime-gate-volume-bar", action="store_true", default=False)

    p.add_argument("--output", type=Path, default=ROOT / "results/v84_backtest_6y_parallel.json")
    p.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    return p.parse_args()


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


def run_one_archive(
    archive: Path,
    args_dict: dict,
    trades_out: Path,
) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/chunk_b_backtest_cached.py"),
        "--dest", str(args_dict["dest"]),
        "--archive", archive.name,
        "--threshold-btc", str(args_dict["threshold_btc"]),
        "--signal-mode", "divergence",
        "--divergence-type", "volume_bar_cvd",
        "--divergence-lookback-bars", str(args_dict["divergence_lookback_bars"]),
        "--exit-after-volume-bars", str(args_dict["exit_after_volume_bars"]),
        "--no-use-time-exit",
        "--stop-pct", str(args_dict["stop_pct"]),
        "--target-pct", str(args_dict["target_pct"]),
        "--no-use-cvd-reversal-confirm",
        "--starting-equity", str(args_dict["starting_equity"]),
        "--base-position-pct", str(args_dict["base_position_pct"]),
        "--entry-lag-bars", str(args_dict["entry_lag_bars"]),
        "--trades-out", str(trades_out),
        "--manifest-jsonl", "/dev/null",
    ]
    if args_dict["scale_target_by_strength"]:
        cmd.append("--scale-target-by-strength")
    if args_dict["use_vpin_gate"]:
        cmd.append("--use-vpin-gate")
    else:
        cmd.append("--no-use-vpin-gate")
    if args_dict["use_market_profile_gate"]:
        cmd.append("--use-market-profile-gate")
    else:
        cmd.append("--no-use-market-profile-gate")
    if args_dict["use_anti_pattern_gate"]:
        cmd.append("--use-anti-pattern-gate")
    else:
        cmd.append("--no-use-anti-pattern-gate")
    if args_dict["use_risk_state_gate"]:
        cmd.append("--use-risk-state-gate")
    else:
        cmd.append("--no-use-risk-state-gate")
    if args_dict["use_auction_state_gate"]:
        cmd.append("--use-auction-state-gate")
    else:
        cmd.append("--no-use-auction-state-gate")
    if args_dict["use_regime_gate_volume_bar"]:
        cmd.append("--use-regime-gate-volume-bar")
    else:
        cmd.append("--no-use-regime-gate-volume-bar")

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": f"/home/tokio/tm-trading-research:{ROOT}"},
    )
    text = proc.stdout.strip()
    if not text:
        if proc.stderr:
            return {"error": proc.stderr[:500], "archive": archive.name}
        proc.check_returncode()
    start = text.find("{")
    if start < 0:
        return {"error": "no json in stdout", "archive": archive.name}
    try:
        payload = json.loads(text[start:])
    except Exception as exc:
        return {"error": f"json load error: {exc}", "archive": archive.name}
    return payload


def load_trades(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    args = parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    all_archives = get_archives(args.dest)

    print(f"Parallel 6y Backtest: {len(all_archives)} archives, workers={args.workers}", flush=True)

    args_dict = {
        "dest": str(args.dest),
        "threshold_btc": args.threshold_btc,
        "divergence_lookback_bars": args.divergence_lookback_bars,
        "exit_after_volume_bars": args.exit_after_volume_bars,
        "stop_pct": args.stop_pct,
        "target_pct": args.target_pct,
        "scale_target_by_strength": args.scale_target_by_strength,
        "starting_equity": args.starting_equity,
        "base_position_pct": args.base_position_pct,
        "entry_lag_bars": args.entry_lag_bars,
        "use_vpin_gate": args.use_vpin_gate,
        "use_market_profile_gate": args.use_market_profile_gate,
        "use_anti_pattern_gate": args.use_anti_pattern_gate,
        "use_risk_state_gate": args.use_risk_state_gate,
        "use_auction_state_gate": args.use_auction_state_gate,
        "use_regime_gate_volume_bar": args.use_regime_gate_volume_bar,
    }

    t0 = time.time()
    futures_map = {}
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for archive in all_archives:
            trades_path = args.work_dir / f"{archive.name}.trades.jsonl"
            fut = executor.submit(run_one_archive, archive, args_dict, trades_path)
            futures_map[fut] = archive

        done = 0
        archive_reports = []
        all_trades = []
        for fut in as_completed(futures_map):
            archive = futures_map[fut]
            done += 1
            payload = fut.result()
            if "error" in payload:
                print(f"Error on {archive.name}: {payload['error']}", file=sys.stderr)
                continue
            archive_reports.append(payload)
            trades_path = args.work_dir / f"{archive.name}.trades.jsonl"
            all_trades.extend(load_trades(trades_path))
            if done % 10 == 0 or done == len(all_archives):
                print(f"Progress: [{done}/{len(all_archives)}]", flush=True)

    # Compile and calculate sequential compounding on sorted trades
    all_trades.sort(key=lambda t: t.get("entry_ts_ns", 0))

    # Chaining compounding equity sequentially
    current_equity = args.starting_equity
    for t in all_trades:
        # Calculate compounded PnL based on position sizing
        pos_size = current_equity * args.base_position_pct
        trade_return = t.get("return_pct", 0.0)
        pnl = pos_size * trade_return
        current_equity += pnl
        t["pnl"] = pnl

    # Recalculate metrics
    returns = [t["return_pct"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]
    sharpe = sharpe_ratio(returns)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / len(all_trades) if all_trades else 0.0

    print(f"\nBacktest completed in {time.time() - t0:.1f}s")
    print(f"Total Trades: {len(all_trades)}")
    print(f"Win Rate: {win_rate:.4%}")
    print(f"Sharpe Ratio: {sharpe:.4f}")
    print(f"Ending Equity: {current_equity:.2f}")

    # Write final summary
    summary = {
        "config": args_dict,
        "report": {
            "trades": len(all_trades),
            "win_rate": round(win_rate, 4),
            "sharpe": round(sharpe, 4),
            "starting_equity": args.starting_equity,
            "ending_equity": round(current_equity, 2),
            "total_pnl": round(current_equity - args.starting_equity, 2),
        }
    }
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
