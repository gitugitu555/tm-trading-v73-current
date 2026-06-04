"""S2 — optional book intelligence via features/ engines."""

from __future__ import annotations

from datetime import datetime, timezone

from core.types import BookSnapshot, SignedTrade as CoreSignedTrade
from features.snapshots import FeatureSnapshotBuilder
from prime.contracts import SignMethod
from v72.contracts import BookIntelligenceSnapshot, V72PipelineState


def _prime_to_core_signed(prime_trade) -> CoreSignedTrade:
    side = "BUY" if prime_trade.side > 0 else "SELL" if prime_trade.side < 0 else "UNKNOWN"
    ts = datetime.fromtimestamp(prime_trade.timestamp_ns / 1_000_000_000, tz=timezone.utc)
    return CoreSignedTrade(
        ts_event=ts,
        exchange=prime_trade.source,
        symbol=prime_trade.symbol,
        price=prime_trade.price,
        size_base=prime_trade.size,
        notional_quote=prime_trade.price * prime_trade.size,
        side=side,
        confidence=prime_trade.sign_confidence,
        method=prime_trade.sign_method.value if isinstance(prime_trade.sign_method, SignMethod) else str(prime_trade.sign_method),
        trade_id=prime_trade.trade_id,
    )


class BookIntelligenceStage:
    stage_id = "s2"

    def __init__(self, *, tick_size: float = 0.1) -> None:
        self._builder = FeatureSnapshotBuilder(tick_size=tick_size)

    def reset(self) -> None:
        self._builder = FeatureSnapshotBuilder(tick_size=self._builder.footprint.tick_size)

    def process(
        self,
        state: V72PipelineState,
        *,
        book: BookSnapshot | None = None,
    ) -> V72PipelineState:
        if state.halted or state.signed_trade is None:
            return state

        if book is not None:
            self._builder.update_book(book)

        core_trade = _prime_to_core_signed(state.signed_trade)
        snapshot = self._builder.update_trade(core_trade)
        ts = state.signed_trade.timestamp_ns
        state.book_intel = BookIntelligenceSnapshot(
            timestamp_ns=ts,
            vpin=snapshot.vpin,
            microprice=snapshot.microprice,
            book_imbalance=snapshot.book_imbalance,
            absorption=snapshot.absorption,
            spoof_regime=snapshot.spoof_regime,
            whale_pressure=snapshot.whale_pressure,
            reason_codes=snapshot.reason_codes,
        )
        state.stage_trace.append(self.stage_id)
        return state