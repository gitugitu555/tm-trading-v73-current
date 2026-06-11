"""Explicit cost replay helpers for V9.0 validation closure."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import statistics
from typing import Any, Callable, Iterable

from research.v86_recovery import summarize_trades
from research.v88_policy_replay import replay_policy


@dataclass(frozen=True)
class CostReplayResult:
    policy_name: str
    mode: str
    fee_bps_per_side: float
    slippage_bps_per_side: float
    hypothetical: bool
    summary: dict[str, Any]
    cost_break_even_threshold_bps: float
    yearly_summary: dict[str, dict[str, Any]]


def explicit_cost_replay(
    signals: list[dict[str, Any]],
    paths: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    *,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    mode: str = "taker",
    signal_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    gross_policy = dict(policy)
    gross_policy["fee_bps_per_side"] = 0.0
    gross_policy["slippage_bps_per_side"] = 0.0
    replay = replay_policy(signals, paths, gross_policy, occupancy_mode=policy.get("occupancy_mode", "independent"), max_concurrent=int(policy.get("max_concurrent", 1)))
    trades = apply_explicit_costs(
        replay["trades"],
        fee_bps_per_side=fee_bps_per_side,
        slippage_bps_per_side=slippage_bps_per_side,
        mode=mode,
        signal_filter=signal_filter,
        signals=signals,
    )
    summary = summarize_trades(trades)
    yearly_summary = _yearly_summary(trades)
    gross_expectancy = statistics.mean(float(row["gross_return_pct"]) for row in trades) if trades else 0.0
    net_expectancy = statistics.mean(float(row["net_return_pct"]) for row in trades) if trades else 0.0
    break_even = max(0.0, (gross_expectancy - net_expectancy) * 10_000.0 / 2.0)
    return {
        "policy_name": policy.get("name", "policy"),
        "mode": mode,
        "fee_bps_per_side": fee_bps_per_side,
        "slippage_bps_per_side": slippage_bps_per_side,
        "hypothetical": mode == "maker",
        "summary": {
            **summary,
            "gross_expectancy": gross_expectancy,
            "net_expectancy": net_expectancy,
            "cost_drag": gross_expectancy - net_expectancy,
        },
        "cost_break_even_threshold_bps": break_even,
        "yearly_summary": yearly_summary,
        "trades": trades,
    }


def apply_explicit_costs(
    trades: Iterable[dict[str, Any]],
    *,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    mode: str = "taker",
    signal_filter: Callable[[dict[str, Any]], bool] | None = None,
    signals: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    lookup = {signal["signal_id"]: signal for signal in signals or []}
    adjusted = []
    cost_fraction = 2.0 * (float(fee_bps_per_side) + float(slippage_bps_per_side)) / 10_000.0
    for row in trades:
        signal = lookup.get(row["signal_id"])
        if signal_filter is not None and signal is not None and not signal_filter(signal):
            continue
        gross = float(row["gross_return_pct"])
        net = gross - cost_fraction
        notional = float(row.get("notional", 100.0))
        adjusted.append(
            {
                **row,
                "mode": mode,
                "hypothetical": mode == "maker",
                "gross_return_pct": gross,
                "net_return_pct": net,
                "return_gross_pct": gross,
                "return_net_pct": net,
                "return_pct": net,
                "pnl_gross": gross * notional,
                "pnl_net": net * notional,
                "pnl": net * notional,
                "fees": notional * 2.0 * float(fee_bps_per_side) / 10_000.0,
                "slippage": notional * 2.0 * float(slippage_bps_per_side) / 10_000.0,
                "entry_cost_bps_per_side": float(fee_bps_per_side),
                "slippage_bps_per_side": float(slippage_bps_per_side),
            }
        )
    return adjusted


def cost_grid() -> list[tuple[float, float]]:
    return [(fee, slip) for fee in (0, 1, 2, 4, 6, 8, 10) for slip in (0, 1, 2, 4, 6, 8, 10)]


def _yearly_summary(trades: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trades:
        ts_ns = int(row.get("signal_ts_ns", row.get("exit_ts_ns", 0)))
        year = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).strftime("%Y")
        grouped[year].append(row)
    return {year: summarize_trades(rows) for year, rows in sorted(grouped.items())}
