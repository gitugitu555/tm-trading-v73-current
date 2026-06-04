"""L2 spoofing and layering detector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SpoofingEvent:
    side: str
    price: float
    score: float
    reason_codes: tuple[str, ...]


class SpoofingDetector:
    def __init__(
        self,
        *,
        min_notional: float = 500_000.0,
        lifetime_ms: int = 2_000,
        fill_ratio_threshold: float = 0.1,
    ) -> None:
        self.min_notional = float(min_notional)
        self.lifetime_ms = lifetime_ms
        self.fill_ratio_threshold = fill_ratio_threshold
        self._large_levels: dict[tuple[str, float], tuple[datetime, float]] = {}

    def update(
        self,
        *,
        ts_event: datetime,
        bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        asks: list[tuple[float, float]] | tuple[tuple[float, float], ...],
    ) -> list[SpoofingEvent]:
        current = self._collect_large_levels(bids, asks)
        events: list[SpoofingEvent] = []

        for key, (first_seen, original_qty) in list(self._large_levels.items()):
            if key in current:
                continue
            age_ms = (ts_event - first_seen).total_seconds() * 1000.0
            if age_ms <= self.lifetime_ms:
                side, price = key
                events.append(
                    SpoofingEvent(
                        side=side,
                        price=price,
                        score=max(0.0, 1.0 - age_ms / self.lifetime_ms),
                        reason_codes=("SPOOF_CANDIDATE", "FAST_WALL_CANCEL"),
                    )
                )
            del self._large_levels[key]

        for key, qty in current.items():
            self._large_levels.setdefault(key, (ts_event, qty))

        return events

    def _collect_large_levels(
        self,
        bids: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        asks: list[tuple[float, float]] | tuple[tuple[float, float], ...],
    ) -> dict[tuple[str, float], float]:
        levels: dict[tuple[str, float], float] = {}
        for side, rows in (("BID", bids), ("ASK", asks)):
            for price, qty in rows:
                if price * qty >= self.min_notional:
                    levels[(side, price)] = qty
        return levels
