#!/usr/bin/env python3
"""Run explicit-cost replay stress tests for the verified V8.9/V9.0 data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.v86_recovery import load_jsonl
from research.v87_execution import execution_summary
from research.v88_policy_replay import replay_policy
from research.v90_cost_model import apply_explicit_costs, cost_grid


def main() -> int:
    signals = load_jsonl(ROOT / "results/v89_data_foundation/verified_signal_ledger/immutable_signal_ledger.jsonl")
    paths = {row["signal_id"]: row for row in load_jsonl(ROOT / "results/v89_data_foundation/verified_trade_paths/trade_paths.jsonl")}
    policy_summary = json.loads((ROOT / "results/v89_data_foundation/v88_verified_replay/policy_summary.json").read_text(encoding="utf-8"))
    selected_policies = {
        "best_v89_policy": policy_summary["results"][policy_summary["ranked"][0]]["policy"],
        "baseline_fixed_tpsl": {"name": "baseline_fixed_tpsl", "target_pct": 0.0055, "stop_pct": 0.03, "bar_exit": 24},
        "best_breakeven_policy": {"name": "best_breakeven_policy", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "breakeven_trigger_mfe_pct": 0.001, "breakeven_lock_pct": 0.001},
        "best_mfe_trailing_policy": {"name": "best_mfe_trailing_policy", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25},
        "single_position_best": {"name": "single_position_best", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25, "occupancy_mode": "single_position", "max_concurrent": 1},
        "cvd_slope_filtered_shadow": {"name": "cvd_slope_filtered_shadow", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25},
        "cvd_accel_filtered_shadow": {"name": "cvd_accel_filtered_shadow", "target_pct": 0.01, "stop_pct": 0.03, "bar_exit": 48, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25},
    }
    outputs = {}
    for label, policy in selected_policies.items():
        replay = replay_policy(signals, paths, {**policy, "fee_bps_per_side": 0.0, "slippage_bps_per_side": 0.0}, occupancy_mode=policy.get("occupancy_mode", "independent"), max_concurrent=int(policy.get("max_concurrent", 1)))
        gross_trades = replay["trades"]
        signal_filter = None
        if label == "cvd_slope_filtered_shadow":
            signal_filter = lambda signal: float(signal.get("cvd_slope", 0.0)) > 0
        elif label == "cvd_accel_filtered_shadow":
            signal_filter = lambda signal: float(signal.get("cvd_accel", 0.0)) > 0
        grid = {}
        for fee_bps, slip_bps in cost_grid():
            adjusted = apply_explicit_costs(gross_trades, fee_bps_per_side=fee_bps, slippage_bps_per_side=slip_bps, mode="taker", signals=signals, signal_filter=signal_filter)
            summary_fields = execution_summary(adjusted)
            summary = {
                "trade_count": len(adjusted),
                "gross_expectancy": sum(float(row["gross_return_pct"]) for row in adjusted) / len(adjusted) if adjusted else 0.0,
                "net_expectancy": sum(float(row["net_return_pct"]) for row in adjusted) / len(adjusted) if adjusted else 0.0,
                "fee_drag": fee_bps,
                "slippage_drag": slip_bps,
                "profit_factor": _profit_factor(adjusted),
                "sharpe": summary_fields["sharpe"],
                "sortino": summary_fields["sortino"],
                "calmar": summary_fields["calmar"],
                "max_drawdown": summary_fields["max_drawdown"],
                "cost_break_even_threshold": max(0.0, (sum(float(row["gross_return_pct"]) for row in adjusted) / len(adjusted) - sum(float(row["net_return_pct"]) for row in adjusted) / len(adjusted)) * 10_000.0 / 2.0),
            }
            grid[f"fee_{fee_bps}_slip_{slip_bps}"] = summary
        reference = apply_explicit_costs(gross_trades, fee_bps_per_side=0.0, slippage_bps_per_side=0.0, mode="taker", signals=signals, signal_filter=signal_filter)
        outputs[label] = {
            "policy": policy,
            "grid": grid,
            "best_net_expectancy": max((row["net_expectancy"] for row in grid.values()), default=0.0),
            "positive_years_after_cost": _positive_years(reference),
        }
    out = ROOT / "results/v90_validation_closure/cost_replay"
    out.mkdir(parents=True, exist_ok=True)
    (out / "explicit_cost_replay.json").write_text(json.dumps(outputs, indent=2, sort_keys=True), encoding="utf-8")
    doc = ROOT / "docs/v90_validation_closure/01_explicit_cost_replay.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# V9.0 Explicit Cost Replay\n\n"
        "Explicit taker-cost replay was run against the verified immutable replay set.\n\n"
        f"Selected policies: {', '.join(sorted(selected_policies))}\n\n"
        "The JSON artifact contains the full fee/slippage grid and break-even thresholds.\n",
        encoding="utf-8",
    )
    return 0


def _profit_factor(trades: list[dict[str, object]]) -> float:
    wins = sum(float(row["pnl_net"]) for row in trades if float(row["pnl_net"]) > 0)
    losses = abs(sum(float(row["pnl_net"]) for row in trades if float(row["pnl_net"]) < 0))
    return wins / losses if losses else (float("inf") if wins else 0.0)


def _positive_years(trades: list[dict[str, object]]) -> list[str]:
    from collections import defaultdict
    from datetime import datetime, timezone

    grouped = defaultdict(list)
    for row in trades:
        year = datetime.fromtimestamp(int(row["signal_ts_ns"]) / 1e9, tz=timezone.utc).strftime("%Y")
        grouped[year].append(float(row["net_return_pct"]))
    return [year for year, values in sorted(grouped.items()) if values and sum(values) / len(values) > 0]


if __name__ == "__main__":
    raise SystemExit(main())
