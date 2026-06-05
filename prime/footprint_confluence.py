"""Footprint confluence filter/score for volume-bar CVD fades.

Enhanced with absorption, stacked imbalance, and conviction scoring
based on sub-agent research synthesis (order flow best practices).
Backward compatible with existing footprint_confirms_fade.
"""

from __future__ import annotations


def footprint_confirms_fade(
    *,
    trade_side: int,
    footprint_bias: int,
    footprint_stacked: bool,
    require_stacked: bool = False,
    allow_neutral: bool = True,
    invert_for_fade: bool = False,
) -> bool:
    """Return True when footprint agrees with fade direction (or is neutral).
    Legacy simple boolean for backward compat in existing backtests.
    """
    expected = -trade_side if invert_for_fade else trade_side
    if footprint_bias == 0:
        return allow_neutral
    if footprint_bias != expected:
        return False
    if require_stacked and not footprint_stacked:
        return False
    return True


def footprint_confluence_score(
    *,
    trade_side: int,
    footprint_bias: int,
    footprint_stacked: bool = False,
    absorption_confirmed: bool = False,
    delta_cluster_strength: float = 0.0,
    require_stacked: bool = False,
    min_score_for_permit: float = 0.5,
) -> float:
    """Return conviction score [0.0, 1.0] for footprint alignment with CVD fade.

    Incorporates research-backed elements:
    - Footprint bias match (core)
    - Stacked imbalance (stronger confirmation)
    - Absorption confirmed (smart money / institutional defense at level)
    - Optional delta cluster strength (from delta velocity/acceleration)

    High score = higher position size or relaxed other gates.
    Low score (< min) can be used to filter or require extra permission.
    """
    if footprint_bias == 0:
        base = 0.4  # neutral footprint still allows but low conviction
    elif footprint_bias == trade_side:
        base = 0.7
    else:
        return 0.0  # opposing bias kills the setup per research

    score = base

    if footprint_stacked:
        score += 0.15  # stacked imbalances are high-probability continuation/exhaustion
    if absorption_confirmed:
        score += 0.20  # absorption at divergence = strong institutional confirmation
    if delta_cluster_strength > 0.5:
        score += 0.10  # strong delta cluster in direction adds edge

    if require_stacked and not footprint_stacked:
        score = max(0.0, score - 0.3)  # penalize if required but missing

    # Cap and ensure in [0,1]
    score = max(0.0, min(1.0, score))

    return round(score, 4)


def should_permit_with_confluence(
    *,
    trade_side: int,
    footprint_bias: int,
    footprint_stacked: bool = False,
    absorption_confirmed: bool = False,
    delta_cluster_strength: float = 0.0,
    min_score: float = 0.5,
) -> bool:
    """Convenience gate: True if confluence score meets minimum for permission."""
    score = footprint_confluence_score(
        trade_side=trade_side,
        footprint_bias=footprint_bias,
        footprint_stacked=footprint_stacked,
        absorption_confirmed=absorption_confirmed,
        delta_cluster_strength=delta_cluster_strength,
    )
    return score >= min_score
