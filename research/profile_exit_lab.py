"""Profile Exit Laboratory — V8.5.

Signal-driven exit engine using POC, VWAP, Value Area and LVN anchors.

Design philosophy (V8.5 upgrade):
  - Entries are filtered by VWAP side alignment and POC proximity.
  - Exits are driven by profile SIGNALS (POC reclaim, VAH/VAL break, VWAP flip)
    rather than fixed-percentage take-profits / stops, so trades can run longer
    when the profile supports them.
  - A hard stop is still enforced (atr-scaled) to cap catastrophic adverse moves.
  - VWAP_DEVIATION is accepted as an entry quality score: entries near VWAP
    (deviation < threshold) are preferred for mean-reversion setups.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from features.market_profile import MarketProfileSnapshot


# ---------------------------------------------------------------------------
# Exit signal taxonomy
# ---------------------------------------------------------------------------

class ExitSignal(str, Enum):
    """Named exit triggers derived from profile geometry."""

    NONE = "NONE"
    """No actionable signal — keep trade open."""

    POC_RECLAIMED = "POC_RECLAIMED"
    """Price returned to / through POC (mean-reversion target hit)."""

    VAH_BREAK = "VAH_BREAK"
    """Price broke above VAH on a long (momentum target hit)."""

    VAL_BREAK = "VAL_BREAK"
    """Price broke below VAL on a short (momentum target hit)."""

    VWAP_FLIP_ADVERSE = "VWAP_FLIP_ADVERSE"
    """Price crossed back through VWAP against the trade direction."""

    POC_FLIP_ADVERSE = "POC_FLIP_ADVERSE"
    """Price crossed POC in the wrong direction (thesis invalidated)."""

    LVN_REJECT = "LVN_REJECT"
    """Price failed at an LVN zone — micro-reversal likely."""

    HARD_STOP = "HARD_STOP"
    """ATR-scaled hard stop — maximum adverse move exceeded."""


# ---------------------------------------------------------------------------
# Entry quality score
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EntryQuality:
    """Profile-based entry quality metrics used to rank / filter signals."""

    poc_distance_pct: float
    """How far the entry price is from POC, as a fraction of POC."""

    vwap_side_aligned: bool
    """True if price is on the correct side of VWAP for the trade direction.
    Long: price below VWAP (mean-reversion) or VWAP rising (momentum).
    Short: price above VWAP or VWAP falling."""

    value_context: str
    """current_value_context from the profile snapshot."""

    entry_score: float
    """Composite [0, 1] score; higher = better quality entry."""

    vwap_deviation: float
    """Signed VWAP deviation at entry time."""

    poc: Optional[float]
    vwap: Optional[float]


def score_entry(
    entry_price: float,
    side: int,
    profile: MarketProfileSnapshot,
    vwap_deviation: float = 0.0,
    *,
    max_poc_distance_pct: float = 0.015,
) -> EntryQuality:
    """Return an EntryQuality for the proposed trade.

    Args:
        entry_price: The prospective fill price.
        side: +1 for long, -1 for short.
        profile: Current MarketProfileSnapshot.
        vwap_deviation: Signed (price - VWAP) / VWAP from the cached column.
        max_poc_distance_pct: Entries more than this % away from POC get a
            lower score (still allowed but deprioritised).
    """
    poc = profile.poc
    vwap_est = entry_price / (1.0 + vwap_deviation) if vwap_deviation != 0 else None

    poc_distance_pct = abs(entry_price - poc) / poc if poc else 1.0

    # VWAP side alignment: longs want price at/below VWAP, shorts at/above
    if vwap_deviation != 0.0:
        if side > 0:
            vwap_side_aligned = vwap_deviation <= 0.0  # price ≤ VWAP
        else:
            vwap_side_aligned = vwap_deviation >= 0.0  # price ≥ VWAP
    else:
        vwap_side_aligned = True  # unknown — assume neutral

    # Composite score
    distance_score = max(0.0, 1.0 - poc_distance_pct / max_poc_distance_pct)
    vwap_score = 1.0 if vwap_side_aligned else 0.4
    context_score = {
        "BELOW_VALUE": 0.9 if side > 0 else 0.6,
        "ABOVE_VALUE": 0.9 if side < 0 else 0.6,
        "IN_VALUE":    0.7,
        "UNKNOWN":     0.5,
    }.get(profile.current_value_context, 0.5)

    entry_score = round((distance_score * 0.35 + vwap_score * 0.35 + context_score * 0.30), 4)

    return EntryQuality(
        poc_distance_pct=round(poc_distance_pct, 6),
        vwap_side_aligned=vwap_side_aligned,
        value_context=profile.current_value_context,
        entry_score=entry_score,
        vwap_deviation=round(vwap_deviation, 6),
        poc=poc,
        vwap=round(vwap_est, 2) if vwap_est else None,
    )


# ---------------------------------------------------------------------------
# Exit decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProfileExitDecision:
    target_price: Optional[float]
    stop_price: Optional[float]
    context: str         # e.g. EXT_TO_POC, POC_REVERSAL, VAH_RESISTANCE
    exit_recommended: bool
    signal: ExitSignal   # NEW — what triggered the recommendation


# ---------------------------------------------------------------------------
# Core exit lab
# ---------------------------------------------------------------------------

class ProfileExitLab:
    """Calculates profile-based exit levels and evaluates trade conditions.

    V8.5 changes:
      * ``detect_exit_signal`` detects POC, VAH/VAL, VWAP-based events.
      * ``evaluate_exit`` uses the detected signal to decide exit, falling
        back to percentage-based hard-stop only when signal is ``NONE``.
      * Trades are allowed to *run* when profile structure supports them.
    """

    def __init__(
        self,
        use_vah_val_bounds: bool = True,
        hard_stop_atr_multiple: float = 2.5,
    ) -> None:
        self.use_vah_val_bounds = use_vah_val_bounds
        self.hard_stop_atr_multiple = hard_stop_atr_multiple

    # ------------------------------------------------------------------
    # Signal detection
    # ------------------------------------------------------------------

    def detect_exit_signal(
        self,
        current_price: float,
        entry_price: float,
        side: int,
        profile: MarketProfileSnapshot,
        vwap_deviation: float = 0.0,
        *,
        base_stop_pct: float = 0.03,
        lvn_reject_margin_pct: float = 0.001,
    ) -> ExitSignal:
        """Detect the strongest active exit signal from the profile.

        Evaluation order (highest priority first):
          1. Hard stop   — percentage-based (base_stop_pct, default 3%)
          2. POC flip    — POC crossed in the wrong direction
          3. VWAP flip   — price moved adversely through VWAP
          4. VAH break   — long target hit at VAH
          5. VAL break   — short target hit at VAL
          6. POC reclaim — mean-reversion target hit
          7. LVN reject  — price stalled at an LVN
        """
        poc = profile.poc
        vah = profile.vah
        val = profile.val

        # 1. Hard stop — percentage-based (reliable for all bar types)
        if base_stop_pct > 0:
            if side > 0 and current_price <= entry_price * (1.0 - base_stop_pct):
                return ExitSignal.HARD_STOP
            if side < 0 and current_price >= entry_price * (1.0 + base_stop_pct):
                return ExitSignal.HARD_STOP


        if poc is None or vah is None or val is None:
            return ExitSignal.NONE

        # 2. POC flip adverse — price crossed back through POC against the trade.
        # For a long: we entered ABOVE poc and price has now dropped back below poc.
        # For a short: we entered BELOW poc and price has now rallied back above poc.
        if poc is not None:
            if side > 0 and entry_price >= poc and current_price < poc * 0.9995:
                return ExitSignal.POC_FLIP_ADVERSE
            if side < 0 and entry_price <= poc and current_price > poc * 1.0005:
                return ExitSignal.POC_FLIP_ADVERSE

        # 3. VWAP flip adverse
        if vwap_deviation != 0.0:
            if side > 0 and vwap_deviation >= 0.005:   # was below VWAP, now above by >0.5%
                return ExitSignal.VWAP_FLIP_ADVERSE
            if side < 0 and vwap_deviation <= -0.005:  # was above VWAP, now below by >0.5%
                return ExitSignal.VWAP_FLIP_ADVERSE

        # 4. VAH break — long momentum target
        if side > 0 and current_price >= vah:
            return ExitSignal.VAH_BREAK

        # 5. VAL break — short momentum target
        if side < 0 and current_price <= val:
            return ExitSignal.VAL_BREAK

        # 6. POC reclaim — mean-reversion target
        if side > 0 and entry_price < poc and current_price >= poc:
            return ExitSignal.POC_RECLAIMED
        if side < 0 and entry_price > poc and current_price <= poc:
            return ExitSignal.POC_RECLAIMED

        # 7. LVN rejection — price tagged an LVN within margin AND POC not yet reached
        poc_reached = (
            (side > 0 and current_price >= poc)
            or (side < 0 and current_price <= poc)
        ) if poc is not None else False
        if not poc_reached:
            for lvn in profile.lvn_zones:
                if abs(current_price - lvn) / max(lvn, 1e-12) <= lvn_reject_margin_pct:
                    # Only exit if the LVN is in the direction of our profit
                    if side > 0 and lvn > entry_price:
                        return ExitSignal.LVN_REJECT
                    if side < 0 and lvn < entry_price:
                        return ExitSignal.LVN_REJECT

        return ExitSignal.NONE

    # ------------------------------------------------------------------
    # Main evaluate method (backward-compatible)
    # ------------------------------------------------------------------

    def evaluate_exit(
        self,
        entry_price: float,
        current_price: float,
        side: int,         # +1 long, -1 short
        profile: MarketProfileSnapshot,
        base_target_pct: float = 0.005,
        base_stop_pct: float = 0.03,
        vwap_deviation: float = 0.0,
    ) -> ProfileExitDecision:
        """Determine target and stop levels with signal-driven exit logic.

        If a strong profile signal is detected the trade exits immediately.
        Otherwise profile anchors (POC, VAH, VAL) become dynamic targets and
        the trade stays open until price reaches them — allowing runs.
        A fallback to percentage-based hard stop is always in effect.
        """
        poc = profile.poc
        vah = profile.vah
        val = profile.val

        # Always detect the current signal first
        sig = self.detect_exit_signal(
            current_price=current_price,
            entry_price=entry_price,
            side=side,
            profile=profile,
            vwap_deviation=vwap_deviation,
        )

        exit_now = sig not in {ExitSignal.NONE}

        if poc is None or vah is None or val is None:
            # Fallback to standard percentage targets/stops if profile is incomplete
            target = (
                entry_price * (1.0 + base_target_pct)
                if side > 0
                else entry_price * (1.0 - base_target_pct)
            )
            stop = (
                entry_price * (1.0 - base_stop_pct)
                if side > 0
                else entry_price * (1.0 + base_stop_pct)
            )
            return ProfileExitDecision(
                target_price=round(target, 6),
                stop_price=round(stop, 6),
                context="FALLBACK_BPS",
                exit_recommended=exit_now,
                signal=sig,
            )

        # ---- Profile-based Target & Stop ----
        if side > 0:
            if entry_price < poc:
                target_price = poc          # Mean reversion to POC
                context = "MEAN_REVERSION_TO_POC"
            else:
                target_price = max(entry_price * (1.0 + 0.001), vah)  # Momentum to VAH
                context = "MOMENTUM_TO_VAH"

            # Dynamic stop: below VAL or ATR-scaled, whichever is tighter
            atr_stop = entry_price * (1.0 - base_stop_pct)
            val_stop = val * 0.998
            stop_price = max(atr_stop, val_stop)

            # Hard stop override using base_stop_pct as backstop
            if current_price <= entry_price * (1.0 - base_stop_pct):
                exit_now = True
                sig = ExitSignal.HARD_STOP

        else:
            if entry_price > poc:
                target_price = poc          # Mean reversion to POC
                context = "MEAN_REVERSION_TO_POC"
            else:
                target_price = min(entry_price * (1.0 - 0.001), val)  # Momentum to VAL
                context = "MOMENTUM_TO_VAL"

            atr_stop = entry_price * (1.0 + base_stop_pct)
            vah_stop = vah * 1.002
            stop_price = min(atr_stop, vah_stop)

            if current_price >= entry_price * (1.0 + base_stop_pct):
                exit_now = True
                sig = ExitSignal.HARD_STOP

        # Price at or beyond profile target — exit
        if side > 0 and current_price >= target_price:
            exit_now = True
        if side < 0 and current_price <= target_price:
            exit_now = True

        return ProfileExitDecision(
            target_price=round(target_price, 6),
            stop_price=round(stop_price, 6),
            context=context,
            exit_recommended=exit_now,
            signal=sig,
        )
