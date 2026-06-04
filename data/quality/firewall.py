"""Hot-path data quality firewall."""

from __future__ import annotations

from datetime import datetime

from core.types import BookSnapshot, DataQualityState, SignedTrade


class DataQualityFirewall:
    def __init__(
        self,
        *,
        max_latency_ms: float = 1_000.0,
        stale_after_ms: float = 5_000.0,
    ) -> None:
        self.max_latency_ms = max_latency_ms
        self.stale_after_ms = stale_after_ms
        self._last_ts: dict[tuple[str, str], datetime] = {}
        self._seen_trade_ids: set[tuple[str, str, str]] = set()

    def check_trade(self, trade: SignedTrade, *, ts_recv: datetime | None = None) -> DataQualityState:
        key = (trade.exchange, trade.symbol)
        reason_codes: list[str] = []
        status = "CLEAN"
        confidence = 1.0

        previous = self._last_ts.get(key)
        if previous and trade.ts_event < previous:
            status = "DEGRADED"
            confidence *= 0.5
            reason_codes.append("TIMESTAMP_BACKWARDS")
        self._last_ts[key] = max(previous or trade.ts_event, trade.ts_event)

        duplicate_rate = 0.0
        if trade.trade_id:
            trade_key = (trade.exchange, trade.symbol, trade.trade_id)
            if trade_key in self._seen_trade_ids:
                status = "DEGRADED"
                confidence *= 0.5
                duplicate_rate = 1.0
                reason_codes.append("DUPLICATE_TRADE_ID")
            self._seen_trade_ids.add(trade_key)

        latency_ms = 0.0
        if ts_recv is not None:
            latency_ms = abs((ts_recv - trade.ts_event).total_seconds() * 1000.0)
            if latency_ms > self.max_latency_ms:
                status = "DEGRADED"
                confidence *= 0.5
                reason_codes.append("LATENCY_SPIKE")

        return DataQualityState(
            status=status,  # type: ignore[arg-type]
            latency_ms=latency_ms,
            duplicate_rate=duplicate_rate,
            confidence_scalar=confidence,
            reason_codes=tuple(reason_codes),
        )

    def check_book(self, book: BookSnapshot, *, now: datetime | None = None) -> DataQualityState:
        reason_codes: list[str] = []
        status = "CLEAN"
        confidence = 1.0
        crossed = book.best_bid >= book.best_ask

        if crossed:
            status = "QUARANTINE"
            confidence = 0.0
            reason_codes.append("CROSSED_BOOK")

        stale = False
        latency_ms = 0.0
        if now is not None:
            latency_ms = abs((now - book.ts_event).total_seconds() * 1000.0)
            stale = latency_ms > self.stale_after_ms
            if stale:
                status = "HALT"
                confidence = 0.0
                reason_codes.append("STALE_FEED")

        return DataQualityState(
            status=status,  # type: ignore[arg-type]
            latency_ms=latency_ms,
            crossed_book=crossed,
            stale_feed=stale,
            confidence_scalar=confidence,
            reason_codes=tuple(reason_codes),
        )
