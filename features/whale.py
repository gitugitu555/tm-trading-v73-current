"""Composite whale pressure from free tape and L2 signals."""

from __future__ import annotations

from dataclasses import dataclass

from features.iceberg import IcebergEvent
from features.large_prints import LargePrintEvent
from features.spoofing import SpoofingEvent


@dataclass(frozen=True)
class WhalePressure:
    pressure: float
    confidence: float
    horizon: str
    source_mix: dict[str, float]
    invalidation: str
    reason_codes: tuple[str, ...]


class WhalePressureEngine:
    def compute(
        self,
        *,
        large_print: LargePrintEvent | None = None,
        book_imbalance: float = 0.0,
        spoofing_events: list[SpoofingEvent] | None = None,
        iceberg_events: list[IcebergEvent] | None = None,
    ) -> WhalePressure:
        score = 0.0
        reason_codes: list[str] = []
        source_mix = {"tape": 0.0, "book": 0.0, "spoof": 0.0, "iceberg": 0.0}

        if large_print is not None and large_print.side in {"BUY", "SELL"}:
            direction = 1.0 if large_print.side == "BUY" else -1.0
            contribution = min(35.0, max(10.0, large_print.z_score * 8.0)) * direction
            score += contribution
            source_mix["tape"] = abs(contribution)
            reason_codes.extend(large_print.reason_codes)

        book_contribution = max(-25.0, min(25.0, book_imbalance * 25.0))
        score += book_contribution
        source_mix["book"] = abs(book_contribution)
        if abs(book_contribution) >= 10.0:
            reason_codes.append("BOOK_WHALE_PRESSURE")

        for event in spoofing_events or []:
            score *= 0.6
            source_mix["spoof"] += event.score * 15.0
            reason_codes.extend(event.reason_codes)

        for event in iceberg_events or []:
            direction = 1.0 if event.side == "BID" else -1.0
            contribution = min(20.0, event.refill_count * 4.0) * direction
            score += contribution
            source_mix["iceberg"] += abs(contribution)
            reason_codes.extend(event.reason_codes)

        score = max(-100.0, min(100.0, score))
        confidence = min(1.0, sum(source_mix.values()) / 60.0)
        invalidation = "opposite large print or failed refill"
        return WhalePressure(
            pressure=score,
            confidence=confidence,
            horizon="FAST",
            source_mix=source_mix,
            invalidation=invalidation,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
        )
