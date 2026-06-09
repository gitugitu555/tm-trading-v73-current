"""Profile Exit Laboratory — V8.4.

Computes target price and stop levels dynamically using Market Profile structures
(Point of Control, Value Area High, Value Area Low, Low Volume Nodes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from features.market_profile import MarketProfileSnapshot

@dataclass(frozen=True)
class ProfileExitDecision:
    target_price: Optional[float]
    stop_price: Optional[float]
    context: str  # e.g., EXT_TO_POC, POC_REVERSAL, VAH_RESISTANCE
    exit_recommended: bool


class ProfileExitLab:
    """Calculates profile-based exit levels and evaluates trade conditions."""

    def __init__(self, use_vah_val_bounds: bool = True) -> None:
        self.use_vah_val_bounds = use_vah_val_bounds

    def evaluate_exit(
        self,
        entry_price: float,
        current_price: float,
        side: int,  # +1 long, -1 short
        profile: MarketProfileSnapshot,
        base_target_pct: float = 0.005,
        base_stop_pct: float = 0.03,
    ) -> ProfileExitDecision:
        """Determines target and stop levels based on entry price and Market Profile state."""
        poc = profile.poc
        vah = profile.vah
        val = profile.val

        if poc is None or vah is None or val is None:
            # Fallback to standard percentage targets/stops if profile is incomplete
            target = entry_price * (1.0 + base_target_pct) if side > 0 else entry_price * (1.0 - base_target_pct)
            stop = entry_price * (1.0 - base_stop_pct) if side > 0 else entry_price * (1.0 + base_stop_pct)
            return ProfileExitDecision(
                target_price=target,
                stop_price=stop,
                context="FALLBACK_BPS",
                exit_recommended=False,
            )

        # Profile-based Target & Stop tuning
        # Long trade: Target is POC if entry is below POC, or VAH if entering inside Value Area
        # Stop is typically placed just below VAL or a significant deviation below POC
        if side > 0:
            if entry_price < poc:
                # Target Point of Control (Mean Reversion)
                target_price = poc
                context = "MEAN_REVERSION_TO_POC"
            else:
                # Momentum to Value Area High
                target_price = max(entry_price * (1.0 + 0.001), vah)
                context = "MOMENTUM_TO_VAH"
            
            # Place stop below Value Area Low (adding room)
            stop_price = min(entry_price * (1.0 - 0.002), val * 0.998)
            exit_recommended = current_price <= stop_price or current_price >= target_price
        else:
            # Short trade
            if entry_price > poc:
                target_price = poc
                context = "MEAN_REVERSION_TO_POC"
            else:
                target_price = min(entry_price * (1.0 - 0.001), val)
                context = "MOMENTUM_TO_VAL"

            stop_price = max(entry_price * (1.0 + 0.002), vah * 1.002)
            exit_recommended = current_price >= stop_price or current_price <= target_price

        return ProfileExitDecision(
            target_price=round(target_price, 6),
            stop_price=round(stop_price, 6),
            context=context,
            exit_recommended=exit_recommended,
        )
