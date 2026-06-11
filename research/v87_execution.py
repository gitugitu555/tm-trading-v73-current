"""Execution-timing research primitives for the V8.7 rescue project."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Iterable, Sequence

from prime.performance import max_drawdown, sharpe_ratio, sortino_ratio
from prime.volume_bars import VolumeBar
from prime.volume_bar_cvd import volume_bar_cvd_signal


PARTIAL_THRESHOLDS = tuple(sorted({value / 10 for value in range(1, 11)} | {0.25, 0.5, 0.75}))


def partial_signal(
    closed_bars: Sequence[VolumeBar],
    partial_bar: VolumeBar,
    *,
    lookback_bars: int = 30,
    htf_change: float = 0.0,
    flat_abs: float = math.inf,
) -> dict[str, Any] | None:
    """Evaluate the final signal rule using only observable partial-bar state."""
    return volume_bar_cvd_signal(
        [*closed_bars, partial_bar],
        lookback_bars=lookback_bars,
        htf_change=htf_change,
        flat_abs=flat_abs,
        timestamp_ns=partial_bar.end_ts_ns,
        price=partial_bar.close,
    )


def classify_partial_predictions(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[float(event["partial_fraction"])].append(event)
    result = {}
    for threshold, rows in sorted(grouped.items()):
        tp = sum(bool(row["partial_signal"]) and bool(row["final_signal"]) and row["partial_side"] == row["final_side"] for row in rows)
        fp = sum(bool(row["partial_signal"]) and (not row["final_signal"] or row["partial_side"] != row["final_side"]) for row in rows)
        fn = sum(not row["partial_signal"] and bool(row["final_signal"]) for row in rows)
        tn = len(rows) - tp - fp - fn
        returns = [float(row.get("signed_forward_return", 0.0)) for row in rows if row["partial_signal"]]
        result[f"{threshold:g}"] = {
            "observations": len(rows),
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
            "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
            "avg_ticks_available": statistics.mean(float(row.get("ticks_after_partial", 0)) for row in rows) if rows else 0.0,
            "avg_time_available_ms": statistics.mean(float(row.get("time_after_partial_ns", 0)) / 1_000_000 for row in rows) if rows else 0.0,
            "expected_signed_forward_return": statistics.mean(returns) if returns else 0.0,
        }
    return result


def timing_ledger(
    events: Iterable[dict[str, Any]],
    *,
    timing_field: str,
    exit_field: str = "horizon_exit_price",
    fee_bps_per_side: float = 5.0,
    slippage_bps_per_side: float = 1.0,
    notional: float = 100.0,
    side_field: str = "final_side",
) -> list[dict[str, Any]]:
    rows = []
    cost_fraction = 2 * (fee_bps_per_side + slippage_bps_per_side) / 10_000
    for event in events:
        entry = event.get(timing_field)
        exit_price = event.get(exit_field)
        side = int(event.get(side_field, event.get("side", 0)) or 0)
        if not entry or not exit_price or side == 0:
            continue
        gross_return = side * (float(exit_price) - float(entry)) / float(entry)
        net_return = gross_return - cost_fraction
        rows.append(
            {
                "signal_id": event.get("signal_id"),
                "side": side,
                "entry_ts_ns": event.get(f"{timing_field}_ts_ns", event.get("final_ts_ns", 0)),
                "exit_ts_ns": event.get("horizon_exit_ts_ns", 0),
                "entry_price": float(entry),
                "exit_price": float(exit_price),
                "notional": notional,
                "pnl_gross": gross_return * notional,
                "pnl_net": net_return * notional,
                "pnl": net_return * notional,
                "return_gross_pct": gross_return,
                "return_net_pct": net_return,
                "return_pct": net_return,
                "fees": notional * 2 * fee_bps_per_side / 10_000,
                "slippage": notional * 2 * slippage_bps_per_side / 10_000,
                "exit_reason": "SIGNAL_HORIZON",
            }
        )
    return rows


def execution_summary(trades: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(trades)
    returns = [float(row.get("return_net_pct", row.get("return_pct", 0.0))) for row in rows]
    pnls = [float(row.get("pnl_net", row.get("pnl", 0.0))) for row in rows]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    curve = [0.0]
    for pnl in pnls:
        curve.append(curve[-1] + pnl)
    gross_loss = abs(sum(losses))
    mdd = max_drawdown([100.0 + value for value in curve])
    annual_return_proxy = statistics.mean(returns) * 365 if returns else 0.0
    return {
        "trades": len(rows),
        "win_rate": len(wins) / len(rows) if rows else 0.0,
        "gross_expectancy": statistics.mean(float(row.get("return_gross_pct", 0.0)) for row in rows) if rows else 0.0,
        "net_expectancy": statistics.mean(returns) if returns else 0.0,
        "avg_win": statistics.mean(wins) if wins else 0.0,
        "avg_loss": statistics.mean(losses) if losses else 0.0,
        "profit_factor": sum(wins) / gross_loss if gross_loss else math.inf if wins else 0.0,
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "calmar": annual_return_proxy / mdd if mdd else 0.0,
        "max_drawdown": mdd,
        "fees": sum(float(row.get("fees", 0.0)) for row in rows),
        "slippage": sum(float(row.get("slippage", 0.0)) for row in rows),
    }


def decay_filter_value(
    baseline: Iterable[dict[str, Any]],
    *,
    max_move_pct: float,
    signal_price_field: str = "lag0_close",
    entry_price_field: str = "lag1_open",
) -> dict[str, Any]:
    rows = list(baseline)
    allowed = []
    blocked = []
    for row in rows:
        signal_price = float(row.get(signal_price_field, 0.0) or 0.0)
        entry_price = float(row.get(entry_price_field, 0.0) or 0.0)
        move = abs(entry_price - signal_price) / signal_price if signal_price else math.inf
        (allowed if move <= max_move_pct else blocked).append(row)
    blocked_winners = [row for row in blocked if float(row.get("pnl_net", row.get("pnl", 0.0))) > 0]
    blocked_losers = [row for row in blocked if float(row.get("pnl_net", row.get("pnl", 0.0))) < 0]
    winner_pnl = sum(float(row.get("pnl_net", row.get("pnl", 0.0))) for row in blocked_winners)
    loser_pnl = sum(float(row.get("pnl_net", row.get("pnl", 0.0))) for row in blocked_losers)
    return {
        "max_move_pct": max_move_pct,
        "trades_allowed": len(allowed),
        "trades_blocked": len(blocked),
        "blocked_winners": len(blocked_winners),
        "blocked_losers": len(blocked_losers),
        "blocked_winner_pnl": winner_pnl,
        "blocked_loser_pnl": loser_pnl,
        "net_filter_value": abs(loser_pnl) - winner_pnl,
        "allowed_summary": execution_summary(allowed),
    }
