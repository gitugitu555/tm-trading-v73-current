"""Feature snapshot builder that composes pure engines."""

from __future__ import annotations

from core.types import BookSnapshot, FeatureSnapshot, SignedTrade
from features.absorption import AbsorptionEngine
from features.cvd import CVDEngine
from features.delta import DeltaEngine
from features.footprint import FootprintEngine
from features.iceberg import IcebergDetector
from features.l2_imbalance import OrderBookImbalanceEngine
from features.large_prints import LargePrintDetector
from features.microprice import microprice
from features.queue_imbalance import QueueImbalanceEngine
from features.spoofing import SpoofingDetector
from features.vpin import VPINEngine
from features.whale import WhalePressureEngine


class FeatureSnapshotBuilder:
    def __init__(self, *, tick_size: float = 0.1) -> None:
        self.cvd = CVDEngine()
        self.delta = DeltaEngine()
        self.footprint = FootprintEngine(tick_size=tick_size)
        self.vpin = VPINEngine()
        self.absorption = AbsorptionEngine(max_price_move=tick_size * 2)
        self.imbalance = OrderBookImbalanceEngine()
        self.queue_imbalance = QueueImbalanceEngine()
        self.large_prints = LargePrintDetector()
        self.spoofing = SpoofingDetector()
        self.iceberg = IcebergDetector()
        self.whale = WhalePressureEngine()
        self._last_book: BookSnapshot | None = None
        self._last_spoof_regime = "NONE"
        self._last_iceberg_side = "NONE"
        self._last_spoof_events = []
        self._last_iceberg_events = []

    def update_book(self, book: BookSnapshot) -> None:
        spoof_events = self.spoofing.update(
            ts_event=book.ts_event,
            bids=book.bids,
            asks=book.asks,
        )
        iceberg_events = self.iceberg.update(bids=book.bids, asks=book.asks)
        if spoof_events:
            self._last_spoof_regime = "SPOOFING_ACTIVE"
        if iceberg_events:
            self._last_iceberg_side = iceberg_events[-1].side
        self._last_spoof_events = spoof_events
        self._last_iceberg_events = iceberg_events
        self._last_book = book

    def update_trade(self, trade: SignedTrade) -> FeatureSnapshot:
        cvd_state = self.cvd.update(trade)
        delta_state = self.delta.update(cvd_state["cvd"])
        self.footprint.update(trade.price, trade.size_base, trade.side)
        vpin_value = self.vpin.update(trade)
        absorption = self.absorption.update(trade)
        large_print = self.large_prints.update(trade)

        book_imbalance = 0.0
        micro = None
        queue_snapshot = None
        if self._last_book is not None:
            book_imbalance = self.imbalance.update(self._last_book.bids, self._last_book.asks)
            queue_snapshot = self.queue_imbalance.update(self._last_book.bids, self._last_book.asks)
            micro = queue_snapshot.microprice if queue_snapshot is not None else microprice(self._last_book.bids, self._last_book.asks)

        whale = self.whale.compute(
            large_print=large_print,
            book_imbalance=book_imbalance,
            spoofing_events=self._last_spoof_events,
            iceberg_events=self._last_iceberg_events,
        )
        reason_codes = tuple(
            code
            for code in (
                *whale.reason_codes,
                absorption if absorption != "NONE" else "",
                self._last_spoof_regime if self._last_spoof_regime != "NONE" else "",
            )
            if code
        )
        return FeatureSnapshot(
            ts_event=trade.ts_event,
            instrument=trade.symbol,
            cvd=cvd_state["cvd"],
            delta_velocity=delta_state["velocity"],
            delta_acceleration=delta_state["acceleration"],
            vpin=vpin_value,
            microprice=micro,
            book_imbalance=book_imbalance,
            queue_imbalance_top1=queue_snapshot.top1 if queue_snapshot is not None else None,
            queue_imbalance_top5=queue_snapshot.top5 if queue_snapshot is not None else None,
            queue_imbalance_top10=queue_snapshot.top10 if queue_snapshot is not None else None,
            queue_pressure_score=(
                queue_snapshot.weighted_imbalance if queue_snapshot is not None else None
            ),
            microprice_drift_bps=(
                queue_snapshot.microprice_drift_bps if queue_snapshot is not None else None
            ),
            absorption=absorption,
            spoof_regime=self._last_spoof_regime,
            iceberg_side=self._last_iceberg_side,
            whale_pressure=whale.pressure,
            reason_codes=reason_codes,
        )
