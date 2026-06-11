#!/usr/bin/env python3
"""Run resumable V8.6 controlled ablations with canonical manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v86_recovery import normalize_trade, summarize_trades, write_jsonl, write_manifest
from storage.hot_path import hot_btcusdt_aggtrades_dir

OUT = ROOT / "results/v86_recovery"
BASE = [
    "--threshold-btc", "300", "--signal-mode", "divergence",
    "--divergence-type", "volume_bar_cvd", "--no-use-time-exit",
    "--no-use-cvd-reversal-confirm", "--starting-equity", "500",
    "--base-position-pct", "0.50", "--scale-target-by-strength",
    "--divergence-lookback-bars", "30", "--exit-after-volume-bars", "24",
    "--stop-pct", "0.03", "--target-pct", "0.0055",
]
CONFIGS = {
    "v86_00_v84_repro_lag0": ["--entry-lag-bars", "0"],
    "v86_01_v84_repro_lag1": ["--entry-lag-bars", "1"],
    "v86_02_v84_repro_lag1_cost0": ["--entry-lag-bars", "1", "--fee-bps-per-side", "0", "--slippage-bps-per-side", "0"],
    "v86_03_v84_repro_lag1_cost1x": ["--entry-lag-bars", "1"],
    "v86_04_v84_repro_lag1_cost2x": ["--entry-lag-bars", "1", "--fee-bps-per-side", "10", "--slippage-bps-per-side", "2"],
    "v86_05_v84_repro_lag1_cost3x": ["--entry-lag-bars", "1", "--fee-bps-per-side", "15", "--slippage-bps-per-side", "3"],
    "v86_10_no_profile_no_gates": ["--entry-lag-bars", "1"],
    "v86_11_profile_all_rules": ["--entry-lag-bars", "1", "--use-profile-exit"],
    "v86_12_profile_no_poc_reclaim": ["--entry-lag-bars", "1", "--use-profile-exit", "--disable-profile-poc-reclaim-exit"],
    "v86_13_profile_poc_reclaim_only": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-poc-reclaim-only"],
    "v86_14_profile_val_vah_only": ["--entry-lag-bars", "1", "--use-profile-exit", "--disable-profile-poc-reclaim-exit"],
    "v86_15_profile_no_hard_stop": ["--entry-lag-bars", "1", "--use-profile-exit", "--disable-profile-hard-stop"],
    "v86_16_profile_min_bars_8": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-exit-min-bars", "8"],
    "v86_17_profile_min_bars_12": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-exit-min-bars", "12"],
    "v86_18_profile_min_profit_0": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-exit-min-profit-pct", "0"],
    "v86_19_profile_min_profit_0_001": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-exit-min-profit-pct", "0.001"],
    "v86_20_profile_require_cvd_confirm": ["--entry-lag-bars", "1", "--use-profile-exit", "--profile-exit-require-cvd-confirm"],
    "v86_30_baseline_no_gates": ["--entry-lag-bars", "1"],
    "v86_31_market_profile_gate_only": ["--entry-lag-bars", "1", "--use-market-profile-gate"],
    "v86_32_risk_state_gate_only": ["--entry-lag-bars", "1", "--use-risk-state-gate"],
    "v86_33_vpin_gate_only": ["--entry-lag-bars", "1", "--use-vpin-gate"],
    "v86_34_anti_pattern_gate_only": ["--entry-lag-bars", "1", "--use-anti-pattern-gate"],
    "v86_35_market_profile_plus_risk_state": ["--entry-lag-bars", "1", "--use-market-profile-gate", "--use-risk-state-gate"],
    "v86_36_risk_state_plus_vpin": ["--entry-lag-bars", "1", "--use-risk-state-gate", "--use-vpin-gate"],
    "v86_37_all_gates": ["--entry-lag-bars", "1", "--use-market-profile-gate", "--use-risk-state-gate", "--use-vpin-gate", "--use-anti-pattern-gate"],
}


def archives(dest: Path) -> list[Path]:
    items = sorted(path for path in dest.glob("BTCUSDT-aggTrades-*.zip") if "_1m" not in path.name)
    daily_months = {match.group(1) for path in items if (match := re.match(r"BTCUSDT-aggTrades-(\d{4}-\d{2})-\d{2}\.zip", path.name))}
    return [path for path in items if not (re.match(r"BTCUSDT-aggTrades-\d{4}-\d{2}\.zip$", path.name) and path.stem.removeprefix("BTCUSDT-aggTrades-") in daily_months)]


def option_value(args: list[str], name: str, default: float) -> float:
    return float(args[args.index(name) + 1]) if name in args else default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", nargs="*", default=list(CONFIGS))
    parser.add_argument("--execute", action="store_true", help="Run archives; default only writes manifests")
    parser.add_argument("--limit-archives", type=int)
    ns = parser.parse_args()
    dest = hot_btcusdt_aggtrades_dir()
    selected_archives = archives(dest)
    if ns.limit_archives:
        selected_archives = selected_archives[: ns.limit_archives]
    summaries = {}
    for label in ns.labels:
        if label not in CONFIGS:
            raise SystemExit(f"unknown label: {label}")
        cli = BASE + CONFIGS[label]
        fee = option_value(cli, "--fee-bps-per-side", 5.0)
        slip = option_value(cli, "--slippage-bps-per-side", 1.0)
        manifest = write_manifest(
            output_path=OUT / "manifests" / f"{label}.json",
            strategy_label=label,
            strategy_description="controlled V8.6 ablation",
            repo_root=ROOT,
            runner_script="scripts/chunk_b_backtest_cached.py",
            cli_args=cli,
            archives=selected_archives,
            execution_model={
                "entry_lag_bars": int(option_value(cli, "--entry-lag-bars", 0)),
                "fee_bps_per_side": fee, "slippage_bps_per_side": slip,
                "entry_price_rule": "signal close for lag0; next bar open for lag1",
                "exit_price_rule": "trigger price then adverse slippage",
                "stop_fill_rule": "configured stop level then adverse slippage",
            },
            position_model={"starting_equity": 500, "base_position_pct": 0.50, "compounding": True},
            feature_flags={name.removeprefix("--").replace("-", "_"): name in cli for name in (
                "--use-profile-exit", "--use-market-profile-gate", "--use-risk-state-gate",
                "--use-vpin-gate", "--use-anti-pattern-gate", "--use-cvd-exit", "--scale-target-by-strength",
            )},
        )
        if not ns.execute:
            summaries[label] = {"args_hash": manifest["args_hash"], "status": "manifest_only"}
            continue
        rows = []
        work = OUT / "work" / label
        work.mkdir(parents=True, exist_ok=True)
        for archive in selected_archives:
            output = work / f"{archive.stem}.jsonl"
            if not output.exists():
                cmd = [sys.executable, str(ROOT / "scripts/chunk_b_backtest_cached.py"), "--dest", str(dest), "--archive", archive.name, "--trades-out", str(output), "--manifest-jsonl", "/dev/null"] + cli
                subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": f"{ROOT}:{os.environ.get('PYTHONPATH', '')}"}, check=False)
            if output.exists():
                for line in output.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        rows.append(normalize_trade(json.loads(line), strategy_label=label, archive=archive.name, fee_bps_per_side=fee, slippage_bps_per_side=slip))
        write_jsonl(OUT / "trades" / f"{label}.jsonl", rows)
        summaries[label] = summarize_trades(rows)
    path = OUT / "controlled_ablation_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summaries, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
