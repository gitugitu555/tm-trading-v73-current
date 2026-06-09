#!/usr/bin/env python3
"""V8.4 institutional sweep on the 6-month validation window."""

from __future__ import annotations

import itertools
import argparse
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
TARGET_WIN = 0.70


@dataclass
class SweepConfig:
    name: str
    target_pct: float
    exit_bars: int
    lookback: int
    use_vpin: bool = False
    use_market_profile: bool = False
    use_anti_pattern: bool = False
    use_risk_state: bool = False
    extra: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=int(os.environ.get("SWEEP_WORKERS", "12")))
    parser.add_argument("--output-all", type=Path, default=ROOT / "results/v84_sweep_institutional_all.json")
    parser.add_argument("--output-summary", type=Path, default=ROOT / "results/v84_sweep_institutional_summary.json")
    return parser.parse_args()


def build_configs() -> list[SweepConfig]:
    configs: list[SweepConfig] = []
    targets = [0.004, 0.005, 0.006]
    exits = [16, 24]
    lookbacks = [30, 40]
    gate_variants = [
        ("baseline", {}),
        ("vpin", {"use_vpin": True}),
        ("profile", {"use_market_profile": True}),
        ("anti_pattern", {"use_anti_pattern": True}),
        ("profile_anti", {"use_market_profile": True, "use_anti_pattern": True}),
        ("all_shadow", {"use_vpin": True, "use_market_profile": True, "use_anti_pattern": True, "use_risk_state": True}),
    ]

    for target, exit_bars, lookback in itertools.product(targets, exits, lookbacks):
        for label, overrides in gate_variants:
            configs.append(
                SweepConfig(
                    name=f"v84_{label}_t{target}_e{exit_bars}_lb{lookback}",
                    target_pct=target,
                    exit_bars=exit_bars,
                    lookback=lookback,
                    **overrides,
                )
            )
    return configs


def config_to_cmd(cfg: SweepConfig, archive: str) -> list[str]:
    cmd = [
        str(PYTHON),
        str(SCRIPT),
        "--archive",
        archive,
        "--threshold-btc",
        "300.0",
        "--signal-mode",
        "divergence",
        "--divergence-type",
        "volume_bar_cvd",
        "--divergence-lookback-bars",
        str(cfg.lookback),
        "--exit-after-volume-bars",
        str(cfg.exit_bars),
        "--stop-pct",
        str(STOP_PCT),
        "--target-pct",
        str(cfg.target_pct),
        "--no-use-time-exit",
        "--no-use-cvd-reversal-confirm",
        "--use-stress-regime",
        "--scale-target-by-strength",
        "--entry-lag-bars",
        "1",
        "--manifest-jsonl",
        "/dev/null",
    ]
    cmd.append("--use-vpin-gate" if cfg.use_vpin else "--no-use-vpin-gate")
    cmd.append("--use-market-profile-gate" if cfg.use_market_profile else "--no-use-market-profile-gate")
    cmd.append("--use-anti-pattern-gate" if cfg.use_anti_pattern else "--no-use-anti-pattern-gate")
    cmd.append("--use-risk-state-gate" if cfg.use_risk_state else "--no-use-risk-state-gate")
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
    except Exception as exc:
        return {"error": f"json load error: {exc}", "archive": archive}

    rep = payload.get("report", {})
    return {
        "archive": archive,
        "trades": rep.get("trades", 0),
        "win_rate": rep.get("win_rate", 0.0),
        "pnl": rep.get("total_pnl", 0.0),
        "signals": rep.get("signals_seen", 0),
        "signal_hit": rep.get("signal_scorecard", {}).get("hit_rate"),
        "shadow_gate_counts": rep.get("shadow_gate_counts", {}),
    }


def run_config(cfg: SweepConfig) -> dict:
    month_results = []
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    combined_shadow: dict[str, int] = {}
    for archive in ARCHIVES_6M:
        result = run_one_archive(cfg, archive)
        if "error" in result and "win_rate" not in result:
            return {"name": cfg.name, "error": result["error"], "archive": archive}
        trades = int(result.get("trades", 0))
        wr = float(result.get("win_rate", 0.0))
        wins = int(round(wr * trades)) if trades else 0
        total_trades += trades
        total_wins += wins
        total_pnl += float(result.get("pnl", 0.0))
        month_results.append(result)
        for key, value in result.get("shadow_gate_counts", {}).items():
            combined_shadow[key] = combined_shadow.get(key, 0) + int(value)

    agg_wr = total_wins / total_trades if total_trades else 0.0
    return {
        "name": cfg.name,
        "config": {
            "stop_pct": STOP_PCT,
            "target_pct": cfg.target_pct,
            "exit_bars": cfg.exit_bars,
            "lookback": cfg.lookback,
            "use_vpin": cfg.use_vpin,
            "use_market_profile": cfg.use_market_profile,
            "use_anti_pattern": cfg.use_anti_pattern,
            "use_risk_state": cfg.use_risk_state,
        },
        "archives": ARCHIVES_6M,
        "total_trades": total_trades,
        "total_wins": total_wins,
        "win_rate": round(agg_wr, 4),
        "total_pnl": round(total_pnl, 2),
        "months": month_results,
        "shadow_gate_counts": dict(sorted(combined_shadow.items())),
        "meets_70": agg_wr >= TARGET_WIN,
    }


def _worker(cfg_dict: dict) -> dict:
    cfg = SweepConfig(**cfg_dict)
    return run_config(cfg)


def main() -> int:
    args = parse_args()
    configs = build_configs()
    workers = args.workers
    print(
        f"Running V8.4 institutional sweep: {len(configs)} configs x {len(ARCHIVES_6M)} months, workers={workers}",
        flush=True,
    )

    cfg_dicts = [
        {
            "name": c.name,
            "target_pct": c.target_pct,
            "exit_bars": c.exit_bars,
            "lookback": c.lookback,
            "use_vpin": c.use_vpin,
            "use_market_profile": c.use_market_profile,
            "use_anti_pattern": c.use_anti_pattern,
            "use_risk_state": c.use_risk_state,
            "extra": list(c.extra),
        }
        for c in configs
    ]

    results: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, cfg): cfg["name"] for cfg in cfg_dicts}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            results.append(row)
            if done % 10 == 0 or done == len(configs):
                best = max((r.get("win_rate", 0.0) for r in results), default=0.0)
                print(f"Progress: [{done}/{len(configs)}] best win_rate={best:.4f}", flush=True)

    results.sort(key=lambda r: (-r.get("win_rate", 0.0), -r.get("total_pnl", 0.0)))
    summary = {
        "objective": "v84_institutional_sweep",
        "configs_tested": len(results),
        "target_win_rate": TARGET_WIN,
        "best_by_win_rate": results[0] if results else None,
        "top_20": results[:20],
        "elapsed_sec": round(time.time() - t0, 1),
    }

    args.output_all.write_text(json.dumps(results, indent=2), encoding="utf-8")
    args.output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nTOP 5 CONFIGURATIONS BY WIN RATE:")
    for row in results[:5]:
        print(
            f"Name: {row.get('name')} | WR: {row.get('win_rate')} | PnL: {row.get('total_pnl')} | Trades: {row.get('total_trades')}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
