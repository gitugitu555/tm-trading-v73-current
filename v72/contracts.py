"""V7.2 staged pipeline contracts — one state object passed between stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from prime.contracts import DataQualitySnapshot, MicrostructureSnapshot, SignedTrade
from prime.phase5_chunkb import AlphaPermission as ChunkBAlphaPermission
from prime.phase4_minimal import RegimeState
from prime.nautilus_compat import TradeTick


@dataclass
class BookIntelligenceSnapshot:
    """Optional L2-derived fields from S2."""

    timestamp_ns: int
    vpin: float
    microprice: float | None
    book_imbalance: float
    absorption: str
    spoof_regime: str
    whale_pressure: float
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SignalCandidate:
    """S4 output — candidate only, not an order."""

    signal_id: str
    timestamp_ns: int
    side: int
    strength: float
    price: float
    strategy: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TradeIntentV72:
    """S6 output — structured intent for downstream execution/backtest layers."""

    instrument_id: str
    direction: int
    urgency: str
    max_notional: float
    entry_type: str
    permission_verdict: str
    permission_kq: float
    reason_codes: tuple[str, ...]


@dataclass
class V72PipelineState:
    """Mutable pipeline state; stages append fields without side channels."""

    tick: TradeTick | None = None
    signed_trade: SignedTrade | None = None
    data_quality: DataQualitySnapshot | None = None
    microstructure: MicrostructureSnapshot | None = None
    book_intel: BookIntelligenceSnapshot | None = None
    regime: RegimeState | None = None
    signal: SignalCandidate | None = None
    permission: ChunkBAlphaPermission | None = None
    trade_intent: TradeIntentV72 | None = None
    memory_object: dict[str, Any] | None = None
    vwap_deviation: float | None = None
    stage_trace: list[str] = field(default_factory=list)
    halted: bool = False
    halt_reason: str | None = None


@dataclass(frozen=True)
class V72PipelineConfig:
    """Which stages run and in what order."""

    stage_order: tuple[str, ...] = ("s0", "s1", "s2", "s3", "s4", "s5", "s6")
    enable_s2_book: bool = True
    enable_s3_regime: bool = True
    enable_s4_signal: bool = True
    enable_s5_permission: bool = True
    enable_s6_memory_risk: bool = True
    source: str = "BINANCE"
    session_id: str = "v72"
    footprint_tick_size: float = 0.5
    cvd_threshold: float = 100.0
    kq_approve: float = 0.55
    base_position_size: float = 0.01
    trade_notional_usdt: float = 1000.0
    use_auction_state_gate: bool = False