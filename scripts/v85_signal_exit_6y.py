#!/usr/bin/env python3
"""V8.5 signal-exit 6-year sweep.

Compares four strategies over the full 6-year BTCUSDT archive:

  A. Baseline v8.4   — fixed bar-count exit (24 bars), no profile exit
  B. Profile Exit    — POC/VWAP/VAH/VAL signal-driven exit, no VWAP entry filter
  C. Profile Exit + VWAP Entry Filter — same + require VWAP side alignment at entry
  D. Profile Exit + min-entry-score 0.55 — quality-gated entries
  E. Profile Exit + VWAP filter + quality gate (combined best)

Results are written to results/v85_signal_exit_6y.json.
"""

from __future__ import annotations

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
RESULT_FILE = ROOT / "results/v85_signal_exit_6y.json"

# ---------------------------------------------------------------------------
# Archive discovery (same logic as v84 sweep)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Strategy configurations
# ---------------------------------------------------------------------------

STRATEGIES = {
    "A_baseline_v84": {
        "description": "v8.4 baseline: fixed bar-count exit (24 bars), no profile exit",
        "extra_args": [
            "--exit-after-volume-bars", "24",
            "--no-use-profile-exit",
        ],
    },
    "B_profile_exit": {
        "description": "Profile signal exit (POC/VWAP/VAH/VAL), bar-count safety net 3x",
        "extra_args": [
            "--exit-after-volume-bars", "24",
            "--use-profile-exit",
            "--use-market-profile-gate",
        ],
    },
    "C_profile_vwap_filter": {
        "description": "Profile exit + VWAP entry side filter (long below VWAP only)",
        "extra_args": [
            "--exit-after-volume-bars", "24",
            "--use-profile-exit",
            "--use-market-profile-gate",
            "--vwap-entry-side-filter",
        ],
    },
    "D_profile_min_score": {
        "description": "Profile exit + min entry quality score 0.55",
        "extra_args": [
            "--exit-after-volume-bars", "24",
            "--use-profile-exit",
            "--use-market-profile-gate",
            "--min-entry-score", "0.55",
        ],
    },
    "E_profile_combined": {
        "description": "Profile exit + VWAP filter + min entry score 0.50 (combined best)",
        "extra_args": [
            "--exit-after-volume-bars", "24",
            "--use-profile-exit",
            "--use-market-profile-gate",
            "--vwap-entry-side-filter",
            "--min-entry-score", "0.50",
        ],
    },
}

# Shared base args (best v8.4 config)
BASE_ARGS = [
    "--threshold-btc", "300",
    "--signal-mode", "divergence",
    "--divergence-type", "volume_bar_cvd",
    "--divergence-lookback-bars", "30",
    "--no-use-time-exit",
    "--stop-pct", "0.03",
    "--target-pct", "0.005",
    "--no-use-cvd-reversal-confirm",
    "--starting-equity", "500.0",
    "--base-position-pct", "0.01",
    "--entry-lag-bars", "1",
    "--scale-target-by-strength",
    "--manifest-jsonl", "/dev/null",
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_archive(archive: Path, dest: Path, strategy_name: str, strategy: dict) -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        trades_out = Path(tmp) / "trades.jsonl"
        cmd = [
            sys.executable,
            str(ROOT / "scripts/chunk_b_backtest_cached.py"),
            "--dest", str(dest),
            "--archive", archive.name,
            "--trades-out", str(trades_out),
        ] + BASE_ARGS + strategy["extra_args"]

        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": f"/home/tokio/tm-trading-research:{ROOT}"},
        )
        if not trades_out.is_file():
            return {"strategy": strategy_name, "archive": archive.name, "trades": [], "error": proc.stderr[:300]}

        trades = []
        with trades_out.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    trades.append(json.loads(line))
        return {"strategy": strategy_name, "archive": archive.name, "trades": trades}


def evaluate_results(all_trades: list[dict], starting_equity: float = 500.0) -> dict:
    if not all_trades:
        return {"trades": 0, "win_rate": 0.0, "sharpe": 0.0, "ending_equity": starting_equity, "total_return_pct": 0.0}

    all_trades.sort(key=lambda t: t.get("entry_ts_ns", 0))
    equity = starting_equity
    for t in all_trades:
        pos_size = equity * 0.01
        pnl = pos_size * t.get("return_pct", 0.0)
        equity += pnl
        t["pnl"] = pnl

    returns = [t["return_pct"] for t in all_trades]
    pnls = [t["pnl"] for t in all_trades]
    sharpe = sharpe_ratio(returns)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / len(all_trades)
    total_return_pct = (equity - starting_equity) / starting_equity

    exit_reasons: dict[str, int] = {}
    for t in all_trades:
        er = t.get("exit_reason", "UNKNOWN")
        exit_reasons[er] = exit_reasons.get(er, 0) + 1

    return {
        "trades": len(all_trades),
        "win_rate": round(win_rate, 4),
        "sharpe": round(sharpe, 4),
        "starting_equity": starting_equity,
        "ending_equity": round(equity, 2),
        "total_return_pct": round(total_return_pct, 4),
        "total_pnl": round(equity - starting_equity, 2),
        "exit_reasons": dict(sorted(exit_reasons.items(), key=lambda x: -x[1])),
    }


def main() -> int:
    dest = DEFAULT_DEST
    all_archives = get_archives(dest)
    print(f"V8.5 Signal-Exit 6y Sweep: {len(all_archives)} archives, {len(STRATEGIES)} strategies", flush=True)

    t0 = time.time()

    # Collect all tasks
    tasks = []
    for sname, sconfig in STRATEGIES.items():
        for archive in all_archives:
            tasks.append((archive, dest, sname, sconfig))

    # Run in parallel (workers capped to avoid thrashing)
    workers = min(24, len(tasks))
    strategy_trades: dict[str, list[dict]] = {s: [] for s in STRATEGIES}

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_archive, *task): task for task in tasks}
        done = 0
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            sname = res["strategy"]
            strategy_trades[sname].extend(res.get("trades", []))
            if done % (len(all_archives) * len(STRATEGIES) // 10 + 1) == 0 or done == len(tasks):
                print(f"  Progress: [{done}/{len(tasks)}]", flush=True)

    print(f"\nAll done in {time.time() - t0:.1f}s\n")

    # Evaluate each strategy
    results = {}
    print(f"{'Strategy':<35} {'Trades':>7} {'WinRate':>8} {'Sharpe':>8} {'EndEquity':>12} {'ReturnPct':>10}")
    print("-" * 85)

    for sname, sconfig in STRATEGIES.items():
        trades = strategy_trades[sname]
        metrics = evaluate_results(trades, starting_equity=500.0)
        results[sname] = {
            "description": sconfig["description"],
            "metrics": metrics,
            "extra_args": sconfig["extra_args"],
        }
        print(
            f"{sname:<35} {metrics['trades']:>7} {metrics['win_rate']:>8.2%} "
            f"{metrics['sharpe']:>8.4f} {metrics['ending_equity']:>12.2f} "
            f"{metrics['total_return_pct']:>10.2%}"
        )

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults written to {RESULT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
