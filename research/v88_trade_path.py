"""Forward bar-path reconstruction for immutable signals."""

from __future__ import annotations

from typing import Any, Sequence

from prime.volume_bars import VolumeBar

TARGETS = (0.0025, 0.005, 0.0075, 0.01)
STOPS = (0.005, 0.01, 0.02, 0.03)
HORIZONS = (8, 16, 24, 32, 48, 72, 96)


def reconstruct_path(signal: dict[str, Any], bars: Sequence[VolumeBar], *, max_bars: int = 96) -> dict[str, Any]:
    idx = int(signal["bar_id"])
    side = int(signal["side_int"])
    entry = float(signal["entry_reference_price"])
    forward = list(bars[idx + 1 : idx + 1 + max_bars])
    favorable = [side * (bar.high - entry) / entry if side > 0 else side * (entry - bar.low) / entry for bar in forward]
    # Explicit formulas avoid directional ambiguity.
    favorable = [((bar.high - entry) / entry if side > 0 else (entry - bar.low) / entry) for bar in forward]
    adverse = [((entry - bar.low) / entry if side > 0 else (bar.high - entry) / entry) for bar in forward]
    returns = [side * (bar.close - entry) / entry for bar in forward]
    mfe = max(favorable, default=0.0)
    mae = max(adverse, default=0.0)
    return {
        "signal_id": signal["signal_id"], "bar_id": idx, "signal_ts_ns": signal["signal_ts_ns"],
        "side": signal["side"], "side_int": side, "entry_price": entry, "forward_bars": len(forward),
        "bars": [
            {"index": offset + 1, "start_ts_ns": bar.start_ts_ns, "end_ts_ns": bar.end_ts_ns,
             "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close,
             "favorable_pct": favorable[offset], "adverse_pct": adverse[offset], "close_return_pct": returns[offset]}
            for offset, bar in enumerate(forward)
        ],
        "max_favorable_excursion_pct": mfe, "max_adverse_excursion_pct": mae,
        "mfe_bar_index": favorable.index(mfe) + 1 if forward else None,
        "mae_bar_index": adverse.index(mae) + 1 if forward else None,
        "first_touch_target": {str(value): _first_touch(favorable, value) for value in TARGETS},
        "first_touch_stop": {str(value): _first_touch(adverse, value) for value in STOPS},
        "return_at_bar_exit": {str(h): returns[h - 1] if len(returns) >= h else None for h in HORIZONS},
        "gave_back_after_mfe_pct": mfe - returns[-1] if returns else 0.0,
        "positive_mfe_before_loss": bool(mfe > 0 and returns and returns[-1] < 0),
    }


def _first_touch(values: list[float], threshold: float) -> int | None:
    return next((idx + 1 for idx, value in enumerate(values) if value >= threshold), None)
