"""Hidden-liquidity / iceberg absorption detector."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IcebergEvent:
    side: str
    price: float
    refill_count: int
    reason_codes: tuple[str, ...]


class IcebergDetector:
    def __init__(self, *, min_refills: int = 3, refill_tolerance: float = 0.1) -> None:
        self.min_refills = min_refills
        self.refill_tolerance = refill_tolerance
        self._last_qty: dict[tuple[str, float], float] = {}
        self._refills: dict[tuple[str, float], int] = {}

    def update(
        self,
        *,
        bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        asks: list[tuple[float, float]] | tuple[tuple[float, float], ...],
    ) -> list[IcebergEvent]:
        events: list[IcebergEvent] = []
        for side, rows in (("BID", bids), ("ASK", asks)):
            for price, qty in rows:
                key = (side, price)
                previous = self._last_qty.get(key)
                if previous is not None and qty > previous * (1.0 + self.refill_tolerance):
                    count = self._refills.get(key, 0) + 1
                    self._refills[key] = count
                    if count >= self.min_refills:
                        events.append(
                            IcebergEvent(
                                side=side,
                                price=price,
                                refill_count=count,
                                reason_codes=("ICEBERG_CANDIDATE", f"{side}_REFILLS"),
                            )
                        )
                self._last_qty[key] = qty
        return events
