"""Shared immutable event and decision types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Side = Literal["BUY", "SELL", "UNKNOWN"]


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class SignedTrade:
    ts_event: datetime
    exchange: str
    symbol: str
    price: float
    size_base: float
    notional_quote: float
    side: Side
    confidence: float
    method: str
    trade_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts_event", ensure_utc(self.ts_event))
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.size_base <= 0:
            raise ValueError("size_base must be positive")
        if self.notional_quote <= 0:
            raise ValueError("notional_quote must be positive")
        if self.side not in {"BUY", "SELL", "UNKNOWN"}:
            raise ValueError("side must be BUY, SELL, or UNKNOWN")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class BookSnapshot:
    ts_event: datetime
    exchange: str
    symbol: str
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]
    sequence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts_event", ensure_utc(self.ts_event))
        if not self.bids or not self.asks:
            raise ValueError("bids and asks are required")
        if self.bids[0][0] >= self.asks[0][0]:
            raise ValueError("book is crossed")

    @property
    def best_bid(self) -> float:
        return self.bids[0][0]

    @property
    def best_ask(self) -> float:
        return self.asks[0][0]

    @property
    def mid(self) -> float:
        return (self.best_bid + self.best_ask) / 2.0


@dataclass(frozen=True)
class DataQualityState:
    status: Literal["CLEAN", "DEGRADED", "QUARANTINE", "HALT"]
    latency_ms: float = 0.0
    duplicate_rate: float = 0.0
    sequence_gap_count: int = 0
    crossed_book: bool = False
    stale_feed: bool = False
    confidence_scalar: float = 1.0
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureSnapshot:
    ts_event: datetime
    instrument: str
    cvd: float = 0.0
    delta_velocity: float = 0.0
    delta_acceleration: float = 0.0
    vpin: float = 0.0
    microprice: float | None = None
    book_imbalance: float = 0.0
    absorption: str = "NONE"
    spoof_regime: str = "NONE"
    iceberg_side: str = "NONE"
    whale_pressure: float = 0.0
    regime: str = "NEUTRAL"
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "ts_event", ensure_utc(self.ts_event))

    def to_row(self) -> dict[str, object]:
        return {
            "ts_event": self.ts_event.isoformat(),
            "instrument": self.instrument,
            "cvd": self.cvd,
            "delta_velocity": self.delta_velocity,
            "delta_acceleration": self.delta_acceleration,
            "vpin": self.vpin,
            "microprice": self.microprice,
            "book_imbalance": self.book_imbalance,
            "absorption": self.absorption,
            "spoof_regime": self.spoof_regime,
            "iceberg_side": self.iceberg_side,
            "whale_pressure": self.whale_pressure,
            "regime": self.regime,
            "reason_codes": "|".join(self.reason_codes),
        }
