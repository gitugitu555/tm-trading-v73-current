from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class BookSnapshot:
    ts_ns: int
    symbol: str
    venue: str
    bid_px: list[float]
    bid_sz: list[float]
    ask_px: list[float]
    ask_sz: list[float]


@dataclass
class MarketStateFrame:
    ts_ns: int
    symbol: str
    side_candidate: Optional[str]
    cvd: float
    cvd_divergence_score: float
    microprice_drift_bps: Optional[float]
    mlofi_w: Optional[float]
    mlofi_depth_scaled: Optional[float]
    queue_imbalance_top5: Optional[float]
    vpin_score: Optional[float]
    toxicity_state: Optional[str]
    atr_used_pct: Optional[float]
    profile_context: Optional[str]
    distance_to_poc_bps: Optional[float]
    dom_entry_quality: Optional[float]
    risk_state: str


@dataclass
class ShadowGateResult:
    gate_id: str
    passed: bool
    score: Optional[float]
    reason: Optional[str]
    would_block: bool
