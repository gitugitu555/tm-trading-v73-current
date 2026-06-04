"""Small dependency-free config helpers."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class EngineConfig:
    symbol: str = "BTCUSDT"
    exchange: str = "BINANCE"
    tick_size: float = 0.1
    large_print_window: int = 100
    large_print_z_threshold: float = 3.0
    spoof_lifetime_ms: int = 2_000
    spoof_min_notional: float = 500_000.0
    iceberg_min_refills: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "tick_size": self.tick_size,
            "large_print_window": self.large_print_window,
            "large_print_z_threshold": self.large_print_z_threshold,
            "spoof_lifetime_ms": self.spoof_lifetime_ms,
            "spoof_min_notional": self.spoof_min_notional,
            "iceberg_min_refills": self.iceberg_min_refills,
        }

    def hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()
