"""Small Nautilus compatibility layer for Chunk A tests and data harnesses.

When Nautilus Trader is installed, imports resolve to real Nautilus types.
When it is not installed, deterministic stand-ins keep Phase 0/1 unit tests
and IC smoke checks runnable without network or binary dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


try:  # pragma: no cover - exercised only when Nautilus is installed.
    from nautilus_trader.indicators.base.indicator import Indicator
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.model.enums import AggressorSide
    from nautilus_trader.model.identifiers import InstrumentId, TradeId
    from nautilus_trader.model.objects import Price, Quantity

    NAUTILUS_AVAILABLE = True
except Exception:  # pragma: no cover - the fallback is covered by local tests.
    NAUTILUS_AVAILABLE = False

    class Indicator:
        def __init__(self, params: list[Any] | None = None) -> None:
            self.params = params or []
            self._initialized = False

        @property
        def initialized(self) -> bool:
            return self._initialized

        def _set_initialized(self) -> None:
            self._initialized = True

    class AggressorSide(str, Enum):
        BUYER = "BUYER"
        SELLER = "SELLER"
        NO_AGGRESSOR = "NO_AGGRESSOR"

    class InstrumentId(str):
        @classmethod
        def from_str(cls, value: str) -> "InstrumentId":
            return cls(value)

    class TradeId(str):
        pass

    class Price:
        def __init__(self, value: float | str, precision: int = 2) -> None:
            self.value = round(float(value), precision)
            self.precision = precision

        def __float__(self) -> float:
            return self.value

        def __str__(self) -> str:
            return f"{self.value:.{self.precision}f}"

    class Quantity:
        def __init__(self, value: float | str, precision: int = 8) -> None:
            self.value = round(float(value), precision)
            self.precision = precision

        def __float__(self) -> float:
            return self.value

        def __str__(self) -> str:
            return f"{self.value:.{self.precision}f}"

    @dataclass(frozen=True)
    class TradeTick:
        instrument_id: InstrumentId
        price: Price
        size: Quantity
        aggressor_side: AggressorSide
        trade_id: TradeId
        ts_event: int
        ts_init: int


def aggressor_name(side: object) -> str:
    return str(getattr(side, "name", side)).upper()

