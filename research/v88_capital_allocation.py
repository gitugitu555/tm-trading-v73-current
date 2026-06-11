"""Capital allocation accounting that cannot change underlying trade returns."""

from __future__ import annotations

from typing import Any


def replay_capital(trades: list[dict[str, Any]], *, starting_equity: float = 500.0, base_position_pct: float = 0.01, drawdown_throttle: bool = False) -> dict[str, Any]:
    equity = starting_equity
    peak = equity
    curve = [equity]
    allocated = []
    for trade in trades:
        scale = 1.0
        dd = (peak - equity) / peak if peak else 0.0
        if drawdown_throttle:
            scale = 0.75 if dd >= 0.05 else scale
            scale = 0.50 if dd >= 0.10 else scale
            scale = 0.25 if dd >= 0.15 else scale
            scale = 0.0 if dd >= 0.20 else scale
        notional = equity * base_position_pct * scale
        pnl = notional * float(trade["net_return_pct"])
        equity += pnl
        peak = max(peak, equity)
        curve.append(equity)
        allocated.append(notional)
    return {
        "starting_equity": starting_equity, "ending_equity": equity,
        "net_pnl": equity - starting_equity,
        "raw_expectancy": sum(float(t["net_return_pct"]) for t in trades) / len(trades) if trades else 0.0,
        "average_capital_used": sum(allocated) / len(allocated) if allocated else 0.0,
        "turnover": sum(allocated), "equity_curve": curve,
    }
