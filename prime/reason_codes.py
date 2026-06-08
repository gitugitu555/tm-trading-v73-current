"""Standardized reason codes for the professional unified strategy.

Used in signal generation, permission chains, scorecards, manifests, and logs.
Enum-based for type safety + easy serialization.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable


class ReasonCode(StrEnum):
    # Core signal
    CORE_CVD_VOLBAR = "CORE_CVD_VOLBAR"
    CORE_CVD_VOLBAR_D5 = "CORE_CVD_VOLBAR_D5"

    # Feed / quality
    FEED_QUALITY = "FEED_QUALITY"

    # Regime (HardRegimeClassifier)
    REGIME_TREND = "REGIME_TREND"
    REGIME_RANGING_FADE = "REGIME_RANGING_FADE"
    REGIME_HALT = "REGIME_HALT"
    REGIME_UNKNOWN = "REGIME_UNKNOWN"
    REGIME_GATE = "REGIME_GATE"

    # Auction (AuctionStateEngine)
    AUCTION_BALANCED = "AUCTION_BALANCED"
    AUCTION_DISCOVERY = "AUCTION_DISCOVERY"
    AUCTION_TRENDING = "AUCTION_TRENDING"
    AUCTION_TRENDING_FADE_PENALTY = "AUCTION_TRENDING_FADE_PENALTY"
    AUCTION_EXHAUSTION = "AUCTION_EXHAUSTION"
    AUCTION_FAILED_BOOST = "AUCTION_FAILED_BOOST"
    AUCTION_FAILED_PENALTY = "AUCTION_FAILED_PENALTY"

    # Footprint / microstructure confluence
    FOOTPRINT_BIAS_MATCH = "FOOTPRINT_BIAS_MATCH"
    FOOTPRINT_BIAS_OPPOSE = "FOOTPRINT_BIAS_OPPOSE"
    FOOTPRINT_STACKED = "FOOTPRINT_STACKED"
    FOOTPRINT_ABSORPTION = "FOOTPRINT_ABSORPTION"
    FOOTPRINT_CONVICTION_HIGH = "FOOTPRINT_CONVICTION_HIGH"
    FOOTPRINT_CONFLUENCE = "FOOTPRINT_CONFLUENCE"

    # Other confluences (per V73 synthesis)
    VPIN_TOXIC = "VPIN_TOXIC"
    VPIN_CONFIRM = "VPIN_CONFIRM"
    L2_IMBALANCE_TRIGGER = "L2_IMBALANCE_TRIGGER"
    L2_MICROPRICE_TRIGGER = "L2_MICROPRICE_TRIGGER"
    WHALE_ALIGN = "WHALE_ALIGN"
    ICEBERG_CONFIRM = "ICEBERG_CONFIRM"
    SPOOF_NEAR = "SPOOF_NEAR"

    # Permission / conversion
    PERMISSION_KQ_APPROVE = "PERMISSION_KQ_APPROVE"
    PERMISSION_KQ_REDUCED = "PERMISSION_KQ_REDUCED"
    PERMISSION_HARD_DENY = "PERMISSION_HARD_DENY"
    CONFLUENCE_BOOST = "CONFLUENCE_BOOST"

    # Legacy / momentum path (for compat)
    CVD_CONFIRMING = "CVD_CONFIRMING"
    CVD_OPPOSING = "CVD_OPPOSING"
    VWAP_STRUCTURE = "VWAP_STRUCTURE"

    # Exits / risk
    EXIT_BAR_COUNT = "EXIT_BAR_COUNT"
    EXIT_OPPOSING_CVD = "EXIT_OPPOSING_CVD"
    EXIT_OPPOSING_FOOTPRINT = "EXIT_OPPOSING_FOOTPRINT"
    EXIT_AUCTION_FLIP = "EXIT_AUCTION_FLIP"
    EXIT_VPIN_SPIKE = "EXIT_VPIN_SPIKE"
    EXIT_TP = "EXIT_TP"
    EXIT_SL = "EXIT_SL"

    @classmethod
    def from_str(cls, value: str) -> "ReasonCode":
        try:
            return cls(value)
        except ValueError:
            return cls("CORE_CVD_VOLBAR")  # safe default

    def to_str(self) -> str:
        return self.value


def codes_to_strings(codes: Iterable[ReasonCode | str]) -> list[str]:
    return [c.value if isinstance(c, ReasonCode) else str(c) for c in codes]


def has_blocker(codes: Iterable[str | ReasonCode], blockers: set[str] | None = None) -> bool:
    if blockers is None:
        blockers = {ReasonCode.REGIME_HALT, ReasonCode.FOOTPRINT_BIAS_OPPOSE, ReasonCode.SPOOF_NEAR}
    return any(str(c) in blockers for c in codes)
