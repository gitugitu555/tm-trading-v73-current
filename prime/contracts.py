"""V7.2 Phase 0 and Phase 1 contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Optional


class SignMethod(str, Enum):
    NATIVE = "NATIVE"
    LEE_READY = "LEE_READY"
    TICK_RULE = "TICK_RULE"
    BVC = "BVC"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SignedTrade:
    trade_id: str
    symbol: str
    timestamp_ns: int
    price: float
    size: float
    side: int
    sign_method: SignMethod
    sign_confidence: float
    source: str
    raw_hash: str
    session_id: str


@dataclass
class DataQualitySnapshot:
    state: str
    latency_ms: float
    duplicate_rate: float
    sequence_gap_count: int
    crossed_book: bool
    stale_feed_ms: float
    confidence_scalar: float
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class MicrostructureSnapshot:
    timestamp_ns: int
    input_hash: str
    cvd_session: float
    cvd_1m: float
    cvd_5m: float
    cvd_divergence: bool
    cvd_trend: str
    delta_velocity: float
    delta_acceleration: float
    exhaustion: str
    dominant_level: Optional[float]
    footprint_bias: int
    footprint_stacked: bool
    vp_poc: Optional[float]
    vp_vah: Optional[float]
    vp_val: Optional[float]
    vp_position: float
    confidence_scalar: float
    trade_count: int


def hash_dict(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]

