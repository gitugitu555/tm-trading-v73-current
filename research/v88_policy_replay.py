"""Occupancy-aware replay over a fixed immutable opportunity set."""

from __future__ import annotations

from typing import Any

from research.v87_execution import execution_summary
from research.v88_tpsl_policies import replay_tpsl


def replay_policy(signals: list[dict[str, Any]], paths: dict[str, dict[str, Any]], policy: dict[str, Any], *, occupancy_mode: str = "independent", max_concurrent: int = 1) -> dict[str, Any]:
    candidates = sorted(signals, key=lambda row: int(row["signal_ts_ns"]))
    trades = []
    active_exits: list[int] = []
    skipped_occupancy = 0
    for signal in candidates:
        ts = int(signal["signal_ts_ns"])
        active_exits = [value for value in active_exits if value > ts]
        cap = len(candidates) if occupancy_mode == "independent" else max_concurrent
        if len(active_exits) >= cap:
            skipped_occupancy += 1
            continue
        path = paths.get(signal["signal_id"])
        if path is None:
            continue
        trade = replay_tpsl(path, policy)
        trades.append(trade)
        active_exits.append(int(trade["exit_ts_ns"]))
    summary = execution_summary(
        [{**trade, "return_pct": trade["net_return_pct"], "pnl": trade["net_return_pct"] * 100,
          "pnl_net": trade["net_return_pct"] * 100, "return_net_pct": trade["net_return_pct"]}
         for trade in trades]
    )
    return {
        "total_candidate_signals": len(candidates), "tradable_signals": len(trades),
        "skipped_due_to_occupancy": skipped_occupancy, "skipped_due_to_filters": 0,
        "executed_trades": len(trades), "opportunity_retention_ratio": len(trades) / len(candidates) if candidates else 0.0,
        "summary": summary, "trades": trades,
    }
