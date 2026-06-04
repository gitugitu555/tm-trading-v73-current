"""Trade signing hierarchy for aggressive side classification."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from core.types import SignedTrade, Side


class TradeSigner:
    """Classify trade aggressor side with native, quote-mid, then tick fallback."""

    def __init__(self) -> None:
        self._last_price: float | None = None
        self._last_side: Side = "UNKNOWN"

    def sign(
        self,
        *,
        ts_event: datetime,
        exchange: str,
        symbol: str,
        price: float,
        size_base: float,
        buyer_is_maker: bool | None = None,
        native_aggressor_side: Side | None = None,
        mid_before: float | None = None,
        trade_id: str | None = None,
    ) -> SignedTrade:
        notional = price * size_base
        side, confidence, method = self._classify(
            price=price,
            buyer_is_maker=buyer_is_maker,
            native_aggressor_side=native_aggressor_side,
            mid_before=mid_before,
        )
        self._last_price = price
        if side != "UNKNOWN":
            self._last_side = side
        return SignedTrade(
            ts_event=ts_event,
            exchange=exchange,
            symbol=symbol,
            price=price,
            size_base=size_base,
            notional_quote=notional,
            side=side,
            confidence=confidence,
            method=method,
            trade_id=trade_id,
        )

    def _classify(
        self,
        *,
        price: float,
        buyer_is_maker: bool | None,
        native_aggressor_side: Side | None,
        mid_before: float | None,
    ) -> tuple[Side, float, str]:
        if native_aggressor_side in {"BUY", "SELL"}:
            return native_aggressor_side, 1.0, "native_aggressor"
        if buyer_is_maker is not None:
            return ("SELL" if buyer_is_maker else "BUY"), 1.0, "binance_buyer_is_maker"
        if mid_before is not None:
            if price > mid_before:
                return "BUY", 0.9, "lee_ready_quote_mid"
            if price < mid_before:
                return "SELL", 0.9, "lee_ready_quote_mid"
        if self._last_price is not None:
            if price > self._last_price:
                return "BUY", 0.7, "tick_rule"
            if price < self._last_price:
                return "SELL", 0.7, "tick_rule"
            if self._last_side != "UNKNOWN":
                return self._last_side, 0.55, "tick_rule_zero_tick"
        return "UNKNOWN", 0.2, "unknown"


def bvc_classify(trade_price: float, mid_before: float, size: float) -> dict[str, float]:
    if trade_price > mid_before:
        return {"buy_volume": size, "sell_volume": 0.0, "confidence": 0.9}
    if trade_price < mid_before:
        return {"buy_volume": 0.0, "sell_volume": size, "confidence": 0.9}
    return {"buy_volume": size * 0.5, "sell_volume": size * 0.5, "confidence": 0.4}


def signed_delta(size: float, side: Literal["BUY", "SELL", "UNKNOWN"]) -> float:
    if side == "BUY":
        return size
    if side == "SELL":
        return -size
    return 0.0
