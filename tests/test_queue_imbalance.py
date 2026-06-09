import unittest

from features.queue_imbalance import QueueImbalanceEngine


class QueueImbalanceTests(unittest.TestCase):
    def test_queue_pressure_is_positive_when_bid_depth_dominates(self) -> None:
        bids = [(100.0, 10.0), (99.5, 8.0), (99.0, 6.0), (98.5, 4.0), (98.0, 2.0)]
        asks = [(100.5, 2.0), (101.0, 3.0), (101.5, 4.0), (102.0, 5.0), (102.5, 6.0)]
        snap = QueueImbalanceEngine().update(bids, asks)
        self.assertGreater(snap.top1, 0.0)
        self.assertGreater(snap.weighted_imbalance, 0.0)
        self.assertGreater(snap.microprice_drift_bps, 0.0)
        self.assertGreater(snap.spread_bps, 0.0)
        self.assertEqual(snap.levels_used, 5)

    def test_empty_book_returns_empty_snapshot(self) -> None:
        snap = QueueImbalanceEngine().update([], [])
        self.assertIsNone(snap.top1)
        self.assertEqual(snap.levels_used, 0)


if __name__ == "__main__":
    unittest.main()
