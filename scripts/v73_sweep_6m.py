#!/usr/bin/env python3
"""6-month parameter sweep on cached indicator parquets (target: 70% trade win rate)."""

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

# Last 6 full months with 300-threshold caches
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
    target_pct: float = 0.006
    exit_bars: int = 5
    lookback: int = 40
    divergence_type: str = "volume_bar_cvd"
    signal_mode: str = "divergence"
    regime_gate: bool = True
    footprint: bool = True
    auction_gate: bool = True
    cvd_confirm: bool = False
    vwap_gate: bool = True
    session_extreme: bool = True
    cvd_quantile: bool = False
    delta_rev_2: bool = False
    invert: bool = False
    stress_regime: bool = True
    extra: list[str] = field(default_factory=list)


def build_configs() -> list[SweepConfig]:
    configs: list[SweepConfig] = []
    targets = [0.003, 0.006, 0.01, 0.015, 0.02, 0.03, 0.05]
    exits = [3, 5, 8, 12, 20, 30]
    lookbacks = [15, 25, 40, 60, 80]

    # Core grid: volume_bar_cvd + 3% stop, vary target/exit/lookback
    for t, e, lb in itertools.product(targets, exits, lookbacks):
        configs.append(
            SweepConfig(
                name=f"vbcvd_t{t}_e{e}_lb{lb}",
                target_pct=t,
                exit_bars=e,
                lookback=lb,
            )
        )

    # Gate / filter ablations on a few promising mid params
    bases = [
        ("mid_a", 0.01, 8, 40),
        ("mid_b", 0.006, 12, 40),
        ("mid_c", 0.02, 5, 25),
        ("wide", 0.05, 20, 60),
        ("tight", 0.003, 3, 15),
    ]
    gate_variants = [
        ("all_gates_off", dict(regime_gate=False, footprint=False, auction_gate=False, vwap_gate=False, session_extreme=False)),
        ("no_regime", dict(regime_gate=False)),
        ("no_footprint", dict(footprint=False)),
        ("no_auction", dict(auction_gate=False)),
        ("no_vwap", dict(vwap_gate=False)),
        ("no_session", dict(session_extreme=False)),
        ("cvd_confirm", dict(cvd_confirm=True)),
        ("cvd_quantile", dict(cvd_quantile=True)),
        ("delta_rev2", dict(delta_rev_2=True)),
        ("invert", dict(invert=True)),
        ("no_stress", dict(stress_regime=False)),
        ("minimal", dict(regime_gate=False, footprint=False, auction_gate=False, vwap_gate=False, session_extreme=False, stress_regime=False)),
        ("max_filters", dict(cvd_confirm=True, cvd_quantile=True, delta_rev_2=True)),
    ]
    for bname, t, e, lb in bases:
        for gname, overrides in gate_variants:
            c = SweepConfig(name=f"{bname}_{gname}", target_pct=t, exit_bars=e, lookback=lb, **overrides)
            configs.append(c)

    # Alternate divergence types
    for div in ("swing", "opposite_delta"):
        for t, e in [(0.006, 5), (0.01, 8), (0.02, 12), (0.03, 20)]:
            configs.append(
                SweepConfig(
                    name=f"{div}_t{t}_e{e}",
                    divergence_type=div,
                    target_pct=t,
                    exit_bars=e,
                    lookback=40,
                )
            )

    # Momentum mode samples
    for t, e in [(0.006, 5), (0.01, 10), (0.02, 15)]:
        configs.append(
            SweepConfig(
                name=f"momentum_t{t}_e{e}",
                signal_mode="momentum",
                divergence_type="opposite_delta",
                target_pct=t,
                exit_bars=e,
            )
        )

    # Subagent-recommended CVD / exit / regime extras (3% stop)
    research_extras = [
        ("cvd_d5_htf15", ["--use-delta-rev-2-entry", "--htf-flat-quantile", "0.15"], dict(lookback=25, target_pct=0.01, exit_bars=8)),
        ("cvd_d5_htf10", ["--use-delta-rev-2-entry", "--htf-flat-quantile", "0.10"], dict(lookback=25, target_pct=0.004, exit_bars=12)),
        ("cvd_quant80", ["--use-cvd-quantile-filter", "--cvd-quantile", "0.80"], dict(target_pct=0.004, exit_bars=12)),
        ("cvd_exit", ["--use-cvd-exit"], dict(target_pct=0.004, exit_bars=12)),
        ("bar_only", ["--no-use-tpsl"], dict(target_pct=0.004, exit_bars=12)),
        ("cvd_exit_bar", ["--use-cvd-exit", "--no-use-tpsl"], dict(exit_bars=12)),
        ("hold15m", ["--hold-ns", "900000000000"], dict(target_pct=0.004, exit_bars=12)),
        ("regime_squeeze", ["--regime-ranging-threshold", "0.0018", "--regime-trend-threshold", "0.0035"], dict(target_pct=0.004, exit_bars=12)),
        ("no_footprint_tight", [], dict(footprint=False, target_pct=0.004, exit_bars=12)),
        ("minimal_exits", ["--no-use-tpsl", "--no-use-regime-gate-volume-bar", "--no-use-footprint-confluence", "--no-use-auction-state-gate"], dict(exit_bars=12, target_pct=0.004)),
    ]
    for name, extra, kw in research_extras:
        base = dict(lookback=40, target_pct=0.006, exit_bars=5)
        base.update(kw)
        configs.append(SweepConfig(name=f"research_{name}", extra=extra, **base))

    # Dedupe by name
    seen: set[str] = set()
    out: list[SweepConfig] = []
    for c in configs:
        if c.name in seen:
            continue
        seen.add(c.name)
        out.append(c)
    return out


def config_to_cmd(cfg: SweepConfig, archive: str) -> list[str]:
    cmd = [
        str(PYTHON),
        str(SCRIPT),
        "--archive",
        archive,
        "--threshold-btc",
        str(THRESHOLD),
        "--signal-mode",
        cfg.signal_mode,
        "--divergence-type",
        cfg.divergence_type,
        "--divergence-lookback-bars",
        str(cfg.lookback),
        "--exit-after-volume-bars",
        str(cfg.exit_bars),
        "--stop-pct",
        str(STOP_PCT),
        "--target-pct",
        str(cfg.target_pct),
        "--use-regime-gate-volume-bar" if cfg.regime_gate else "--no-use-regime-gate-volume-bar",
        "--use-footprint-confluence" if cfg.footprint else "--no-use-footprint-confluence",
        "--use-auction-state-gate" if cfg.auction_gate else "--no-use-auction-state-gate",
        "--use-cvd-reversal-confirm" if cfg.cvd_confirm else "--no-use-cvd-reversal-confirm",
        "--use-vwap-gate" if cfg.vwap_gate else "--no-use-vwap-gate",
        "--use-session-extreme-gate" if cfg.session_extreme else "--no-use-session-extreme-gate",
        "--use-cvd-quantile-filter" if cfg.cvd_quantile else "--no-use-cvd-quantile-filter",
        "--use-delta-rev-2-entry" if cfg.delta_rev_2 else "--no-use-delta-rev-2-entry",
        "--use-stress-regime" if cfg.stress_regime else "--no-use-stress-regime",
        "--manifest-jsonl",
        "/dev/null",
    ]
    if cfg.invert:
        cmd.append("--invert-signal-side")
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
    payload = json.loads(text[start:])
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
        cache = ROOT / "results/indicator_cache" / f"{arch}.threshold-{int(THRESHOLD)}.parquet"
        if not cache.is_file():
            return {"name": cfg.name, "error": f"missing cache {arch}"}
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
            "divergence_type": cfg.divergence_type,
            "signal_mode": cfg.signal_mode,
            "regime_gate": cfg.regime_gate,
            "footprint": cfg.footprint,
            "auction_gate": cfg.auction_gate,
            "cvd_confirm": cfg.cvd_confirm,
            "vwap_gate": cfg.vwap_gate,
            "session_extreme": cfg.session_extreme,
            "cvd_quantile": cfg.cvd_quantile,
            "delta_rev_2": cfg.delta_rev_2,
            "invert": cfg.invert,
            "stress_regime": cfg.stress_regime,
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
    out_path = ROOT / "results/v73_sweep_6m_results.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    configs = build_configs()
    workers = int(os.environ.get("SWEEP_WORKERS", "4"))
    print(f"Sweep: {len(configs)} configs x {len(ARCHIVES_6M)} months, stop={STOP_PCT}, workers={workers}", flush=True)

    cfg_dicts = [
        {
            "name": c.name,
            "target_pct": c.target_pct,
            "exit_bars": c.exit_bars,
            "lookback": c.lookback,
            "divergence_type": c.divergence_type,
            "signal_mode": c.signal_mode,
            "regime_gate": c.regime_gate,
            "footprint": c.footprint,
            "auction_gate": c.auction_gate,
            "cvd_confirm": c.cvd_confirm,
            "vwap_gate": c.vwap_gate,
            "session_extreme": c.session_extreme,
            "cvd_quantile": c.cvd_quantile,
            "delta_rev_2": c.delta_rev_2,
            "invert": c.invert,
            "stress_regime": c.stress_regime,
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
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
            flag = " *** 70%+" if row.get("meets_70") else ""
            print(
                f"[{done}/{len(configs)}] {row.get('name')} "
                f"wr={row.get('win_rate')} trades={row.get('total_trades')} "
                f"pnl={row.get('total_pnl')}{flag}",
                flush=True,
            )

    results.sort(key=lambda r: (-r.get("win_rate", 0), -r.get("total_trades", 0)))
    summary_path = ROOT / "results/v73_sweep_6m_summary.json"
    winners = [r for r in results if r.get("meets_70")]
    summary = {
        "stop_pct": STOP_PCT,
        "archives_6m": ARCHIVES_6M,
        "configs_tested": len(results),
        "target_win_rate": TARGET_WIN,
        "winners_70_plus": winners,
        "top_20": results[:20],
        "elapsed_sec": round(time.time() - t0, 1),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if winners else 1


if __name__ == "__main__":
    sys.exit(main())