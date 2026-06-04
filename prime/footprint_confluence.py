"""Footprint confluence filter for volume-bar CVD fades."""

from __future__ import annotations


def footprint_confirms_fade(
    *,
    trade_side: int,
    footprint_bias: int,
    footprint_stacked: bool,
    require_stacked: bool = False,
) -> bool:
    """Return True when footprint agrees with fade direction (or is neutral)."""
    if footprint_bias == 0:
        return True
    if footprint_bias != trade_side:
        return False
    if require_stacked and not footprint_stacked:
        return False
    return True