"""Pure TPSL policies over reconstructed immutable trade paths."""

from __future__ import annotations

from typing import Any


def replay_tpsl(path: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    entry = float(path["entry_price"])
    side = int(path["side_int"])
    target = float(policy.get("target_pct", 0.005))
    stop = float(policy.get("stop_pct", 0.03))
    bar_exit = int(policy.get("bar_exit", 24))
    be_trigger = policy.get("breakeven_trigger_mfe_pct")
    be_lock = float(policy.get("breakeven_lock_pct", 0.0))
    trail_start = policy.get("trail_start_mfe_pct")
    trail_giveback = float(policy.get("trail_giveback_pct", 0.5))
    no_mfe = policy.get("no_mfe_threshold_pct")
    no_mfe_bars = policy.get("exit_if_no_mfe_by_bars")
    max_mfe = 0.0
    protected_floor = -stop
    for row in path["bars"][:bar_exit]:
        idx = int(row["index"])
        favorable = float(row["favorable_pct"])
        adverse = float(row["adverse_pct"])
        max_mfe = max(max_mfe, favorable)
        if favorable >= target and adverse >= stop:
            if policy.get("same_bar_touch_rule", "stop_first") == "target_first":
                return _result(path, idx, target, "TARGET", policy)
            return _result(path, idx, -stop, "STOP", policy)
        if favorable >= target:
            return _result(path, idx, target, "TARGET", policy)
        if be_trigger is not None and max_mfe >= float(be_trigger) and idx >= int(policy.get("min_bars_before_be", 1)):
            protected_floor = max(protected_floor, be_lock)
        if trail_start is not None and max_mfe >= float(trail_start) and idx >= int(policy.get("min_bars_before_trail", 1)):
            protected_floor = max(protected_floor, max_mfe * (1.0 - trail_giveback))
        if adverse >= stop:
            return _result(path, idx, -stop, "STOP", policy)
        if protected_floor >= 0 and float(row["close_return_pct"]) <= protected_floor:
            return _result(path, idx, protected_floor, "MFE_PROTECT", policy)
        if no_mfe is not None and no_mfe_bars is not None and idx >= int(no_mfe_bars) and max_mfe < float(no_mfe):
            return _result(path, idx, float(row["close_return_pct"]), "NO_MFE_TIME_STOP", policy)
    rows = path["bars"][:bar_exit]
    final = float(rows[-1]["close_return_pct"]) if rows else 0.0
    return _result(path, len(rows), final, "BAR_EXIT", policy)


def _result(path: dict[str, Any], bars_held: int, gross_return: float, reason: str, policy: dict[str, Any]) -> dict[str, Any]:
    cost = 2 * (float(policy.get("fee_bps_per_side", 5)) + float(policy.get("slippage_bps_per_side", 1))) / 10_000
    return {
        "signal_id": path["signal_id"], "signal_ts_ns": path["signal_ts_ns"], "side": path["side"],
        "side_int": path["side_int"], "entry_price": path["entry_price"], "bars_held": bars_held,
        "exit_ts_ns": path["bars"][bars_held - 1]["end_ts_ns"] if bars_held and path["bars"] else path["signal_ts_ns"],
        "gross_return_pct": gross_return, "net_return_pct": gross_return - cost, "exit_reason": reason,
        "max_favorable_excursion_pct": path["max_favorable_excursion_pct"],
        "max_adverse_excursion_pct": path["max_adverse_excursion_pct"],
    }
