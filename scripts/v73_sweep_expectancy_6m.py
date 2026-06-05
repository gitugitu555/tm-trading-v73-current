#!/usr/bin/env python3
"""6m expectancy sweep: invert + wide targets + 3% stop (optimize PnL/Sharpe, not WR)."""

from __future__ import annotations

import itertools
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = Path(os.environ.get("TM_RESEARCH_ROOT", "/home/tokio/tm-trading-research"))
sys.path.insert(0, str(ROOT))

from scripts.v73_sweep_6m import (  # noqa: E402
    ARCHIVES_6M,
    STOP_PCT,
    THRESHOLD,
    SweepConfig,
    config_to_cmd,
)

PYTHON = ROOT / ".venv/bin/python"
SCRIPT = ROOT / "scripts/chunk_b_backtest_cached.py"
START_EQUITY = 100_000.0


@dataclass
class ExpConfig(SweepConfig):
    use_cvd_exit: bool = False
    use_tpsl: bool = True


def build_configs() -> list[ExpConfig]:
    configs: list[ExpConfig] = []
    targets = [0.006, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05]
    exits = [8, 12, 20, 30]
    lookbacks = [40, 80, 100]

    for t, e, lb in itertools.product(targets, exits, lookbacks):
        configs.append(
            ExpConfig(
                name=f"exp_t{t}_e{e}_lb{lb}",
                invert=True,
                regime_gate=False,
                footprint=False,
                auction_gate=False,
                vwap_gate=False,
                session_extreme=False,
                target_pct=t,
                exit_bars=e,
                lookback=lb,
            )
        )

    for t, e, lb in [(0.02, 20, 80), (0.03, 20, 100), (0.015, 12, 100)]:
        configs.append(
            ExpConfig(
                name=f"exp_cvd_{t}",
                invert=True,
                regime_gate=False,
                footprint=False,
                auction_gate=False,
                vwap_gate=False,
                session_extreme=False,
                target_pct=t,
                exit_bars=e,
                lookback=lb,
                use_cvd_exit=True,
            )
        )
        configs.append(
            ExpConfig(
                name=f"exp_bar_{t}",
                invert=True,
                regime_gate=False,
                footprint=False,
                auction_gate=False,
                vwap_gate=False,
                session_extreme=False,
                target_pct=t,
                exit_bars=e,
                lookback=lb,
                use_tpsl=False,
            )
        )

    return configs


def exp_to_cmd(cfg: ExpConfig, archive: str, starting_equity: float) -> list[str]:
    cmd = config_to_cmd(cfg, archive)
    # config_to_cmd already has invert; ensure gates off via cfg
    if "--starting-equity" not in cmd:
        idx = cmd.index(str(SCRIPT)) + 1
        cmd = cmd[:idx] + cmd[idx:]
    # Insert starting equity before manifest
    manifest_i = cmd.index("--manifest-jsonl")
    cmd[manifest_i:manifest_i] = ["--starting-equity", str(starting_equity)]
    if cfg.use_cvd_exit:
        cmd.insert(manifest_i, "--use-cvd-exit")
    if not cfg.use_tpsl:
        cmd.insert(manifest_i, "--no-use-tpsl")
    if not cfg.vwap_gate:
        # config_to_cmd may still pass default vwap on - fix by replacing
        pass
    return cmd


def run_one(cfg: ExpConfig, archive: str, starting_equity: float) -> dict:
    import subprocess

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{RESEARCH_ROOT}:{ROOT}"
    cmd = config_to_cmd(cfg, archive)
    # Patch starting equity
    if "--starting-equity" in cmd:
        i = cmd.index("--starting-equity")
        cmd[i + 1] = str(starting_equity)
    else:
        manifest_i = cmd.index("--manifest-jsonl")
        cmd = cmd[:manifest_i] + ["--starting-equity", str(starting_equity)] + cmd[manifest_i:]
    if cfg.use_cvd_exit and "--use-cvd-exit" not in cmd:
        manifest_i = cmd.index("--manifest-jsonl")
        cmd = cmd[:manifest_i] + ["--use-cvd-exit"] + cmd[manifest_i:]
    if not cfg.use_tpsl:
        manifest_i = cmd.index("--manifest-jsonl")
        cmd = cmd[:manifest_i] + ["--no-use-tpsl"] + cmd[manifest_i:]
    # Force gates off for expectancy path
    for a, b in [
        ("--use-vwap-gate", "--no-use-vwap-gate"),
        ("--use-session-extreme-gate", "--no-use-session-extreme-gate"),
    ]:
        if a in cmd:
            cmd[cmd.index(a)] = b
        elif b not in cmd:
            manifest_i = cmd.index("--manifest-jsonl")
            cmd = cmd[:manifest_i] + [b] + cmd[manifest_i:]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    text = proc.stdout.strip()
    if not text:
        return {"error": proc.stderr[:400], "archive": archive}
    start = text.find("{")
    if start < 0:
        return {"error": "no json", "archive": archive}
    payload = json.loads(text[start:])
    rep = payload.get("report", {})
    return {
        "archive": archive,
        "trades": int(rep.get("trades", 0)),
        "win_rate": float(rep.get("win_rate", 0.0)),
        "pnl": float(rep.get("total_pnl", 0.0)),
        "sharpe": float(rep.get("sharpe", 0.0)),
        "ending_equity": float(rep.get("ending_equity", starting_equity)),
        "exit_reasons": rep.get("exit_reasons", {}),
    }


def run_config(cfg: ExpConfig) -> dict:
    equity = START_EQUITY
    months: list[dict] = []
    sharpes: list[float] = []
    weights: list[int] = []
    for arch in ARCHIVES_6M:
        cache = ROOT / "results/indicator_cache" / f"{arch}.threshold-{int(THRESHOLD)}.parquet"
        if not cache.is_file():
            return {"name": cfg.name, "error": f"missing cache {arch}"}
        r = run_one(cfg, arch, equity)
        if "error" in r and "ending_equity" not in r:
            return {"name": cfg.name, "error": r["error"], "archive": arch}
        months.append(r)
        equity = float(r["ending_equity"])
        t = int(r.get("trades", 0))
        if t:
            sharpes.append(float(r.get("sharpe", 0.0)))
            weights.append(t)

    total_trades = sum(m["trades"] for m in months)
    total_pnl = round(equity - START_EQUITY, 2)
    total_return_pct = round((equity / START_EQUITY - 1) * 100, 3)
    avg_sharpe = (
        round(sum(s * w for s, w in zip(sharpes, weights)) / sum(weights), 4)
        if weights
        else 0.0
    )
    wins = sum(int(round(m["win_rate"] * m["trades"])) for m in months)
    agg_wr = round(wins / total_trades, 4) if total_trades else 0.0

    return {
        "name": cfg.name,
        "config": {
            "invert": cfg.invert,
            "stop_pct": STOP_PCT,
            "target_pct": cfg.target_pct,
            "exit_bars": cfg.exit_bars,
            "lookback": cfg.lookback,
            "use_cvd_exit": cfg.use_cvd_exit,
            "use_tpsl": cfg.use_tpsl,
        },
        "total_trades": total_trades,
        "win_rate": agg_wr,
        "total_pnl": total_pnl,
        "ending_equity": round(equity, 2),
        "total_return_pct": total_return_pct,
        "avg_sharpe": avg_sharpe,
        "months": months,
        "profitable": total_pnl > 0,
    }


def main() -> int:
    configs = build_configs()
    out = ROOT / "results/v73_sweep_expectancy_6m.jsonl"
    out.unlink(missing_ok=True)
    results: list[dict] = []
    t0 = time.time()
    print(f"Expectancy sweep: {len(configs)} configs, invert+wide targets, stop={STOP_PCT}", flush=True)

    for i, cfg in enumerate(configs, 1):
        row = run_config(cfg)
        results.append(row)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        print(
            f"[{i}/{len(configs)}] {row.get('name')} "
            f"pnl={row.get('total_pnl')} ret%={row.get('total_return_pct')} "
            f"sharpe={row.get('avg_sharpe')} wr={row.get('win_rate')} trades={row.get('total_trades')}",
            flush=True,
        )

    # Rank: profitable first, then pnl, then sharpe
    results.sort(
        key=lambda r: (
            not r.get("profitable", False),
            -r.get("total_pnl", 0),
            -r.get("avg_sharpe", 0),
        )
    )
    summary = {
        "objective": "expectancy_sharpe",
        "stop_pct": STOP_PCT,
        "invert": True,
        "configs_tested": len(results),
        "profitable_count": sum(1 for r in results if r.get("profitable")),
        "best_by_pnl": results[0] if results else None,
        "top_15": results[:15],
        "elapsed_sec": round(time.time() - t0, 1),
    }
    path = ROOT / "results/v73_sweep_expectancy_6m_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"best": results[0]["name"], "pnl": results[0]["total_pnl"], "sharpe": results[0]["avg_sharpe"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())