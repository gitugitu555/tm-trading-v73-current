import unittest

from features.absorption import AbsorptionEngine
from features.cvd import CVDEngine
from features.delta import DeltaEngine
from features.footprint import FootprintEngine
from features.l2_imbalance import OrderBookImbalanceEngine
from features.mlofi import MLOFIEngine
from features.microprice import microprice
from features.snapshots import FeatureSnapshotBuilder
from features.vpin import VPINEngine
from core.types import BookSnapshot
from tests.helpers import ts
from tests.helpers import trade


class CoreFeatureTest(unittest.TestCase):
    def test_cvd_ignores_unknown_side(self):
        engine = CVDEngine()
        self.assertEqual(engine.update(trade(size=2.0, side="BUY")), {"delta": 2.0, "cvd": 2.0})
        self.assertEqual(engine.update(trade(size=1.0, side="SELL")), {"delta": -1.0, "cvd": 1.0})
        self.assertEqual(engine.update(trade(size=9.0, side="UNKNOWN")), {"delta": 0.0, "cvd": 1.0})

    def test_footprint_groups_by_tick(self):
        engine = FootprintEngine(tick_size=0.5)
        level, row = engine.update(100.24, 2.0, "BUY")
        self.assertEqual(level, 100.0)
        self.assertEqual(row["buy_volume"], 2.0)
        level, row = engine.update(100.26, 1.0, "SELL")
        self.assertEqual(level, 100.5)
        self.assertEqual(row["sell_volume"], 1.0)

    def test_delta_velocity_and_acceleration(self):
        engine = DeltaEngine()
        self.assertEqual(engine.update(10.0), {"velocity": 0.0, "acceleration": 0.0})
        self.assertEqual(engine.update(15.0), {"velocity": 5.0, "acceleration": 5.0})
        self.assertEqual(engine.update(17.0), {"velocity": 2.0, "acceleration": -3.0})

    def test_vpin_absolute_imbalance(self):
        engine = VPINEngine(window=3)
        self.assertEqual(engine.update(trade(size=3.0, side="BUY")), 1.0)
        self.assertEqual(engine.update(trade(size=1.0, side="SELL")), 0.5)

    def test_vpin_volume_bar_snapshot(self):
        engine = VPINEngine()
        self.assertEqual(engine.update_volume_bar(3.0, 1.0).vpin_level, 0.5)
        self.assertEqual(engine.snapshot.vpin_level, 0.5)

    def test_microprice_and_l2_imbalance(self):
        bids = [(99.0, 10.0), (98.5, 5.0)]
        asks = [(101.0, 2.0), (101.5, 5.0)]
        self.assertGreater(microprice(bids, asks), 100.0)
        self.assertGreater(OrderBookImbalanceEngine().update(bids, asks), 0.0)

    def test_feature_snapshot_builder_emits_queue_fields(self):
        builder = FeatureSnapshotBuilder()
        book = BookSnapshot(
            ts_event=ts(),
            exchange="BINANCE",
            symbol="BTCUSDT",
            bids=((100.0, 10.0), (99.5, 8.0), (99.0, 6.0)),
            asks=((100.5, 2.0), (101.0, 3.0), (101.5, 4.0)),
        )
        builder.update_book(book)
        snapshot = builder.update_trade(trade(price=100.25, size=1.0, side="BUY"))
        self.assertIsNotNone(snapshot.queue_imbalance_top1)
        self.assertIsNotNone(snapshot.queue_pressure_score)
        self.assertIsNotNone(snapshot.microprice_drift_bps)

    def test_mlofi_weighted_aggregate(self):
        bids = [(100.0, 10.0), (99.5, 8.0), (99.0, 6.0)]
        asks = [(100.5, 2.0), (101.0, 3.0), (101.5, 4.0)]
        snap = MLOFIEngine(max_levels=3).update(bids, asks)
        self.assertGreater(snap.mlofi_weighted_aggregate, 0.0)
        self.assertEqual(snap.levels_used, 3)

    def test_absorption_detects_bid_absorption(self):
        engine = AbsorptionEngine(window=3, delta_threshold=5.0, max_price_move=1.0)
        self.assertEqual(engine.update(trade(second=0, price=100.0, size=2.0, side="SELL")), "NONE")
        self.assertEqual(engine.update(trade(second=1, price=99.8, size=2.0, side="SELL")), "NONE")
        self.assertEqual(
            engine.update(trade(second=2, price=99.9, size=2.0, side="SELL")),
            "BID_ABSORPTION",
        )


if __name__ == "__main__":
    unittest.main()
