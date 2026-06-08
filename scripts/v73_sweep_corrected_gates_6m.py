#!/usr/bin/env python3
"""6-month parameter sweep on cached indicator parquets with corrected exits (no time exit) and gates."""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = Path(os.environ.get("TM_RESEARCH_ROOT", "/home/tokio/tm-trading-research"))
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

STOP_PCT = 0.03
THRESHOLD = 300.0
TARGET_WIN = 0.70

@dataclass
class SweepConfig:
    name: str
    target_pct: float
    exit_bars: int
    lookback: int
    use_footprint: bool = False
    footprint_require_stacked: bool = False
    footprint_allow_neutral: bool = True
    use_auction: bool = False
    use_regime: bool = False
    use_vwap: bool = False
    approve_only: bool = False
    extra: list[str] = field(default_factory=list)

def build_configs() -> list[SweepConfig]:
    configs: list[SweepConfig] = []
    
    # Base parameters we want to test:
    # 40 lookback with 12/16 exits and 0.004, 0.005, 0.006 targets
    targets = [0.004, 0.005, 0.006]
    exits = [12, 16]
    lookbacks = [40, 60]
    
    # Define the gate variants to test
    gate_variants = [
        # baseline (all gates off)
        ("baseline", {}),
        # footprint variations
        ("footprint_bias", {"use_footprint": True}),
        ("footprint_stacked", {"use_footprint": True, "footprint_require_stacked": True}),
        ("footprint_no_neutral", {"use_footprint": True, "footprint_allow_neutral": False}),
        # single gates
        ("auction", {"use_auction": True}),
        ("regime", {"use_regime": True}),
        ("vwap", {"use_vwap": True}),
        ("approve_only", {"approve_only": True}),
        # combinations
        ("footprint_auction", {"use_footprint": True, "use_auction": True}),
        ("footprint_regime", {"use_footprint": True, "use_regime": True}),
        ("footprint_vwap", {"use_footprint": True, "use_vwap": True}),
        ("footprint_approve", {"use_footprint": True, "approve_only": True}),
        ("auction_regime", {"use_auction": True, "use_regime": True}),
        ("all_gates", {"use_footprint": True, "use_auction": True, "use_regime": True, "use_vwap": True, "approve_only": True}),
    ]
    
    for t, e, lb in itertools.product(targets, exits, lookbacks):
        for gname, overrides in gate_variants:
            cfg_name = f"gate_{gname}_t{t}_e{e}_lb{lb}"
            configs.append(
                SweepConfig(
                    name=cfg_name,
                    target_pct=t,
                    exit_bars=e,
                    lookback=lb,
                    **overrides
                )
            )
            
    return configs

def config_to_cmd(cfg: SweepConfig, archive: str) -> list[str]:
    cmd = [
        str(PYTHON),
        str(SCRIPT),
        "--archive", archive,
        "--threshold-btc", str(THRESHOLD),
        "--signal-mode", "divergence",
        "--divergence-type", "volume_bar_cvd",
        "--divergence-lookback-bars", str(cfg.lookback),
        "--exit-after-volume-bars", str(cfg.exit_bars),
        "--stop-pct", str(STOP_PCT),
        "--target-pct", str(cfg.target_pct),
        "--no-use-time-exit",
        "--use-regime-gate-volume-bar" if cfg.use_regime else "--no-use-regime-gate-volume-bar",
        "--use-footprint-confluence" if cfg.use_footprint else "--no-use-footprint-confluence",
        "--use-auction-state-gate" if cfg.use_auction else "--no-use-auction-state-gate",
        "--use-vwap-gate" if cfg.use_vwap else "--no-use-vwap-gate",
        "--no-use-cvd-reversal-confirm",
        "--use-stress-regime",
        "--manifest-jsonl", "/dev/null",
    ]
    
    if cfg.footprint_require_stacked:
        cmd.append("--footprint-require-stacked")
    if not cfg.footprint_allow_neutral:
        cmd.append("--no-footprint-allow-neutral")
    if cfg.approve_only:
        cmd.append("--approve-only-permission")
        
    cmd.extend(cfg.extra)
    return cmd

def run_one_archive(cfg: SweepConfig, archive: str) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{RESEARCH_ROOT}:{ROOT}"
    proc = subprocess.run(
        config_to_cmd(cfg, archive),
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    text = proc.stdout.strip()
    if not text:
        return {"error": proc.stderr[:500], "archive": archive}
    start = text.find("{")
    if start < 0:
        return {"error": "no json", "archive": archive}
    try:
        payload = json.loads(text[start:])
    except Exception as e:
        return {"error": f"json load error: {e}", "archive": archive}
        
    rep = payload.get("report", {})
    return {
        "archive": archive,
        "trades": rep.get("trades", 0),
        "win_rate": rep.get("win_rate", 0.0),
        "pnl": rep.get("total_pnl", 0.0),
        "signals": rep.get("signals_seen", 0),
        "signal_hit": rep.get("signal_scorecard", {}).get("hit_rate"),
    }

def run_config(cfg: SweepConfig) -> dict:
    month_results = []
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    for arch in ARCHIVES_6M:
        r = run_one_archive(cfg, arch)
        if "error" in r and "win_rate" not in r:
            return {"name": cfg.name, "error": r["error"], "archive": arch}
        trades = int(r.get("trades", 0))
        wr = float(r.get("win_rate", 0.0))
        wins = int(round(wr * trades)) if trades else 0
        total_trades += trades
        total_wins += wins
        total_pnl += float(r.get("pnl", 0.0))
        month_results.append(r)
    agg_wr = total_wins / total_trades if total_trades else 0.0
    return {
        "name": cfg.name,
        "config": {
            "stop_pct": STOP_PCT,
            "target_pct": cfg.target_pct,
            "exit_bars": cfg.exit_bars,
            "lookback": cfg.lookback,
            "use_footprint": cfg.use_footprint,
            "footprint_require_stacked": cfg.footprint_require_stacked,
            "footprint_allow_neutral": cfg.footprint_allow_neutral,
            "use_auction": cfg.use_auction,
            "use_regime": cfg.use_regime,
            "use_vwap": cfg.use_vwap,
            "approve_only": cfg.approve_only,
        },
        "archives": ARCHIVES_6M,
        "total_trades": total_trades,
        "total_wins": total_wins,
        "win_rate": round(agg_wr, 4),
        "total_pnl": round(total_pnl, 2),
        "months": month_results,
        "meets_70": agg_wr >= TARGET_WIN,
    }

def _worker(cfg_dict: dict) -> dict:
    cfg = SweepConfig(**cfg_dict)
    return run_config(cfg)

def main() -> int:
    configs = build_configs()
    workers = int(os.environ.get("SWEEP_WORKERS", "16"))
    print(f"Running gates sweep: {len(configs)} configs x {len(ARCHIVES_6M)} months, workers={workers}", flush=True)
    
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
    
    results: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, d): d["name"] for d in cfg_dicts}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            results.append(row)
            if done % 10 == 0 or done == len(configs):
                print(f"Progress: [{done}/{len(configs)}] done. Best win_rate so far: {max(r.get('win_rate', 0.0) for r in results)}", flush=True)
                
    results.sort(key=lambda r: (-r.get("win_rate", 0.0), -r.get("total_pnl", 0.0)))
    
    summary = {
        "objective": "corrected_gates_sweep",
        "configs_tested": len(results),
        "target_win_rate": TARGET_WIN,
        "best_by_win_rate": results[0] if results else None,
        "top_20": results[:20],
        "elapsed_sec": round(time.time() - t0, 1),
    }
    
    output_path = ROOT / "results/v73_sweep_corrected_gates_6m_summary.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    
    # Print the top 5
    print("\nTOP 5 CONFIGURATIONS BY WIN RATE:")
    for r in results[:5]:
        print(f"Name: {r.get('name')} | WR: {r.get('win_rate')} | PnL: {r.get('total_pnl')} | Trades: {r.get('total_trades')}")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
