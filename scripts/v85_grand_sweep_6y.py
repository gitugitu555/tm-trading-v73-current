#!/usr/bin/env python3
"""V8.5 Master 6-Year Grand Sweep — run ALL strategy families.

Covers:
  - v8.3 baselines (balanced, high-WR, swing)
  - v8.4 configs (1-5 from sweep + institutional winner)
  - v8.5 signal-exit variants (profile exit, VWAP filter, quality gate, combined)
  - v8.5 parameter search grid (lookback × exit_bars × target)
  - v8.5 gate combos (VPIN, anti-pattern, risk-state, all)

All variants run over the full 6-year BTCUSDT archive.
Starting equity: $500 with compounding.
Results written to results/v85_grand_sweep_6y.json
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

from prime.performance import sharpe_ratio, daily_sharpe_ratio, sortino_ratio, daily_sortino_ratio, max_drawdown
from storage.hot_path import hot_btcusdt_aggtrades_dir

DEST = hot_btcusdt_aggtrades_dir()
RESULT_FILE = ROOT / "results/v85_grand_sweep_6y.json"
WORK_DIR = ROOT / "results/v85_grand_sweep_work"
STARTING_EQUITY = 500.0


# ---------------------------------------------------------------------------
# Archive discovery
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
# Strategy registry
# ---------------------------------------------------------------------------

# Shared base — best v8.4 core
BASE = [
    "--threshold-btc", "300",
    "--signal-mode", "divergence",
    "--divergence-type", "volume_bar_cvd",
    "--no-use-time-exit",
    "--no-use-cvd-reversal-confirm",
    "--starting-equity", str(STARTING_EQUITY),
    "--base-position-pct", "0.50",
    "--entry-lag-bars", "1",
    "--scale-target-by-strength",
    "--manifest-jsonl", "/dev/null",
]


def S(name: str, desc: str, extra: list[str]) -> dict:
    return {"name": name, "desc": desc, "extra": extra}


STRATEGIES = [
    # ---- v8.3 legacy baselines ----
    S("v83_balanced",     "v8.3 balanced (t=0.005 e=24 lb=30)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005"]),
    S("v83_highwr",       "v8.3 high-WR (t=0.004 e=16 lb=40)",
      ["--divergence-lookback-bars", "40", "--exit-after-volume-bars", "16",
       "--stop-pct", "0.025", "--target-pct", "0.004"]),
    S("v83_wide",         "v8.3 wide targets (t=0.006 e=24 lb=30)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.035", "--target-pct", "0.006"]),

    # ---- Apples-to-apples normalizations ----
    S("v85_apples_legacy", "v85 logic but with v84 config parameters",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.035", "--target-pct", "0.0055",
       "--entry-lag-bars", "0", "--base-position-pct", "0.50",
       "--no-scale-target-by-strength"]),
    S("v85_apples_lag_only", "v84 config parameters but entry lag 1",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.035", "--target-pct", "0.0055",
       "--entry-lag-bars", "1", "--base-position-pct", "0.50",
       "--no-scale-target-by-strength"]),

    # ---- v8.4 institutional sweep winners ----
    S("v84_config2",      "v8.4 config2 — best sweep winner (t=0.005 e=24 lb=30)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005"]),
    S("v84_config2_profile", "v8.4 config2 + market-profile gate",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-market-profile-gate"]),
    S("v84_config2_allgates", "v8.4 config2 + all shadow gates",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-market-profile-gate", "--use-anti-pattern-gate",
       "--use-vpin-gate", "--use-risk-state-gate"]),
    S("v84_t0045_e20",    "v8.4 t=0.0045 e=20 lb=30",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "20",
       "--stop-pct", "0.025", "--target-pct", "0.0045"]),
    S("v84_t0055_e24",    "v8.4 t=0.0055 e=24 lb=30",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.0055"]),

    # ---- v8.5 signal-exit variants ----
    S("v85_profile_exit", "v8.5 profile signal exit (POC/VWAP/VAH/VAL)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_vwap_filter",  "v8.5 profile exit + VWAP entry side filter",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--vwap-entry-side-filter"]),
    S("v85_quality_50",   "v8.5 profile exit + min entry score 0.50",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--min-entry-score", "0.50"]),
    S("v85_quality_55",   "v8.5 profile exit + min entry score 0.55",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--min-entry-score", "0.55"]),
    S("v85_combined",     "v8.5 combined: VWAP filter + min score 0.50",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--vwap-entry-side-filter", "--min-entry-score", "0.50"]),
    S("v85_combined_anti","v8.5 combined + anti-pattern gate",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--vwap-entry-side-filter", "--min-entry-score", "0.50",
       "--use-anti-pattern-gate"]),
    S("v85_all_gates",    "v8.5 profile exit + ALL gates",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate",
       "--vwap-entry-side-filter", "--min-entry-score", "0.50",
       "--use-anti-pattern-gate", "--use-vpin-gate", "--use-risk-state-gate"]),

    # ---- v8.5 parameter grid on best gates ----
    S("v85_lb20_e20",     "v8.5 lookback=20 exit=20",
      ["--divergence-lookback-bars", "20", "--exit-after-volume-bars", "20",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_lb30_e32",     "v8.5 lookback=30 exit=32",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "32",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_lb40_e24",     "v8.5 lookback=40 exit=24",
      ["--divergence-lookback-bars", "40", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_t0045_profile","v8.5 target=0.0045 with profile exit",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.025", "--target-pct", "0.0045",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_t0055_profile","v8.5 target=0.0055 with profile exit",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.035", "--target-pct", "0.0055",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_t006_profile", "v8.5 target=0.006 with profile exit (run longer)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "32",
       "--stop-pct", "0.035", "--target-pct", "0.006",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_tight_stop",   "v8.5 tighter stop=0.02 with profile exit",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.02", "--target-pct", "0.005",
       "--use-profile-exit", "--use-market-profile-gate"]),
    S("v85_wide_stop",    "v8.5 wider stop=0.04 with profile exit (let winners run)",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "36",
       "--stop-pct", "0.04", "--target-pct", "0.006",
       "--use-profile-exit", "--use-market-profile-gate"]),

    # ---- v8.5 VPIN-only and risk-state only ----
    S("v85_vpin_only",    "v8.5 profile exit + VPIN toxicity gate only",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-vpin-gate"]),
    S("v85_risk_only",    "v8.5 profile exit + risk-state gate only",
      ["--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
       "--stop-pct", "0.03", "--target-pct", "0.005",
       "--use-profile-exit", "--use-risk-state-gate"]),
]


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------

def run_archive(archive: Path, strategy: dict, trades_dir: Path) -> dict:
    trades_out = trades_dir / f"{strategy['name']}_{archive.stem}.jsonl"
    if trades_out.is_file():
        try:
            trades = []
            if trades_out.stat().st_size > 0:
                with trades_out.open(encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            trades.append(json.loads(line))
            return {"strategy": strategy["name"], "archive": archive.name, "trades": trades}
        except Exception:
            pass

    cmd = (
        [sys.executable, str(ROOT / "scripts/chunk_b_backtest_cached.py"),
         "--dest", str(DEST), "--archive", archive.name,
         "--trades-out", str(trades_out)]
        + BASE
        + strategy["extra"]
    )
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": f"/home/tokio/tm-trading-research:{ROOT}"},
    )
    if not trades_out.is_file():
        return {"strategy": strategy["name"], "archive": archive.name, "trades": [], "err": proc.stderr[:200]}
    trades = []
    with trades_out.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                trades.append(json.loads(line))
    return {"strategy": strategy["name"], "archive": archive.name, "trades": trades}


def evaluate(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0, "win_rate": 0.0, "sharpe": 0.0,
            "daily_sharpe": 0.0, "sortino": 0.0, "daily_sortino": 0.0, "max_drawdown": 0.0,
            "starting_equity": STARTING_EQUITY, "ending_equity": STARTING_EQUITY,
            "total_return_pct": 0.0, "total_pnl": 0.0, "exit_reasons": {},
        }
    trades.sort(key=lambda t: t.get("entry_ts_ns", 0))
    eq = STARTING_EQUITY
    for t in trades:
        pnl = eq * 0.01 * t.get("return_pct", 0.0)
        eq += pnl
        t["_pnl"] = pnl

    returns = [t["return_pct"] for t in trades]
    wins = sum(1 for t in trades if t["_pnl"] > 0)
    exit_reasons: dict[str, int] = {}
    for t in trades:
        er = t.get("exit_reason", "?")
        exit_reasons[er] = exit_reasons.get(er, 0) + 1

    # Calculate daily equity and daily returns
    daily_equity = {1: STARTING_EQUITY} # dummy day 1 if no trades
    if len(trades) > 0:
        current_day = trades[0].get("exit_ts_ns", 0) // (24 * 3_600_000_000_000)
        daily_equity = {current_day: STARTING_EQUITY}
        running_equity = STARTING_EQUITY
        for trade in trades:
            day = trade.get("exit_ts_ns", 0) // (24 * 3_600_000_000_000)
            running_equity += trade.get("_pnl", 0)
            daily_equity[day] = running_equity
    
    sorted_days = sorted(daily_equity.keys())
    daily_returns = []
    for i in range(1, len(sorted_days)):
        prev_eq = daily_equity[sorted_days[i-1]]
        curr_eq = daily_equity[sorted_days[i]]
        if prev_eq > 0:
            daily_returns.append((curr_eq - prev_eq) / prev_eq)
        else:
            daily_returns.append(0.0)

    equity_curve = [STARTING_EQUITY]
    running_eq = STARTING_EQUITY
    for trade in trades:
        running_eq += trade.get("_pnl", 0)
        equity_curve.append(running_eq)

    return {
        "trades": len(trades),
        "win_rate": round(wins / len(trades), 4),
        "sharpe": round(sharpe_ratio(returns), 4),
        "daily_sharpe": round(daily_sharpe_ratio(daily_returns), 4),
        "sortino": round(sortino_ratio(returns), 4),
        "daily_sortino": round(daily_sortino_ratio(daily_returns), 4),
        "max_drawdown": round(max_drawdown(equity_curve), 4),
        "starting_equity": STARTING_EQUITY,
        "ending_equity": round(eq, 2),
        "total_return_pct": round((eq - STARTING_EQUITY) / STARTING_EQUITY, 4),
        "total_pnl": round(eq - STARTING_EQUITY, 2),
        "exit_reasons": dict(sorted(exit_reasons.items(), key=lambda x: -x[1])),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    all_archives = get_archives(DEST)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    total_tasks = len(STRATEGIES) * len(all_archives)
    print(
        f"V8.5 Grand Sweep | {len(STRATEGIES)} strategies × {len(all_archives)} archives"
        f" = {total_tasks} tasks | workers=24",
        flush=True,
    )

    t0 = time.time()
    strat_trades: dict[str, list[dict]] = {s["name"]: [] for s in STRATEGIES}

    tasks = [
        (archive, strat, WORK_DIR)
        for strat in STRATEGIES
        for archive in all_archives
    ]

    with ProcessPoolExecutor(max_workers=24) as pool:
        futures = {pool.submit(run_archive, *task): task for task in tasks}
        done = 0
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            strat_trades[res["strategy"]].extend(res.get("trades", []))
            if done % max(1, total_tasks // 20) == 0 or done == total_tasks:
                elapsed = time.time() - t0
                eta = elapsed / done * (total_tasks - done) if done else 0
                print(
                    f"  [{done:>5}/{total_tasks}] "
                    f"elapsed={elapsed:.0f}s  ETA≈{eta:.0f}s",
                    flush=True,
                )

    elapsed = time.time() - t0
    print(f"\nAll done in {elapsed:.1f}s\n", flush=True)

    # Evaluate & rank
    results = {}
    ranked = []
    hdr = f"{'Strategy':<30} {'Trd':>6} {'WR':>7} {'TrdShrp':>7} {'DlyShrp':>7} {'DlySrtn':>7} {'MDD':>7} {'EndEq':>10} {'Ret%':>8}"
    print(hdr)
    print("-" * len(hdr))
    for strat in STRATEGIES:
        sname = strat["name"]
        metrics = evaluate(strat_trades[sname])
        results[sname] = {"description": strat["desc"], "metrics": metrics, "args": strat["extra"]}
        ranked.append((sname, metrics))
        print(
            f"{sname:<30} {metrics['trades']:>6} {metrics['win_rate']:>7.2%} "
            f"{metrics['sharpe']:>7.2f} {metrics['daily_sharpe']:>7.2f} {metrics['daily_sortino']:>7.2f} "
            f"{metrics['max_drawdown']:>7.2%} {metrics['ending_equity']:>10.2f} "
            f"{metrics['total_return_pct']:>8.2%}"
        )

    # Top 5 by Sharpe
    ranked.sort(key=lambda x: -x[1]["sharpe"])
    print(f"\n{'='*60}")
    print("TOP 5 BY SHARPE RATIO")
    print(f"{'='*60}")
    for i, (sname, m) in enumerate(ranked[:5], 1):
        print(
            f"  {i}. {sname}\n"
            f"     Sharpe={m['sharpe']:.4f}  WR={m['win_rate']:.2%}  "
            f"Trades={m['trades']}  Equity=${m['ending_equity']:.2f}  "
            f"Return={m['total_return_pct']:.2%}"
        )

    # Top 5 by Return %
    ranked.sort(key=lambda x: -x[1]["total_return_pct"])
    print(f"\nTOP 5 BY TOTAL RETURN %")
    print(f"{'='*60}")
    for i, (sname, m) in enumerate(ranked[:5], 1):
        print(
            f"  {i}. {sname}\n"
            f"     Return={m['total_return_pct']:.2%}  Sharpe={m['sharpe']:.4f}  "
            f"WR={m['win_rate']:.2%}  Equity=${m['ending_equity']:.2f}"
        )

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results → {RESULT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
