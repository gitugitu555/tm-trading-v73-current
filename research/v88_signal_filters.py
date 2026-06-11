"""Blocked-winner/blocked-loser value accounting on immutable signals."""

from __future__ import annotations

from typing import Any, Callable


def filter_value(signals: list[dict[str, Any]], trades_by_signal: dict[str, dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    allowed = [signal for signal in signals if predicate(signal)]
    blocked = [signal for signal in signals if not predicate(signal)]
    blocked_trades = [trades_by_signal[s["signal_id"]] for s in blocked if s["signal_id"] in trades_by_signal]
    winners = [t for t in blocked_trades if float(t["net_return_pct"]) > 0]
    losers = [t for t in blocked_trades if float(t["net_return_pct"]) < 0]
    winner_pnl = sum(float(t["net_return_pct"]) for t in winners)
    loser_pnl = sum(float(t["net_return_pct"]) for t in losers)
    return {
        "signals_allowed": len(allowed), "signals_blocked": len(blocked),
        "blocked_winners": len(winners), "blocked_losers": len(losers),
        "blocked_winner_pnl": winner_pnl, "blocked_loser_pnl": loser_pnl,
        "net_filter_value": abs(loser_pnl) - winner_pnl,
    }
