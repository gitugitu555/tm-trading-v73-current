import unittest

from features.iceberg import IcebergDetector
from features.large_prints import LargePrintDetector
from features.spoofing import SpoofingDetector
from features.whale import WhalePressureEngine
from tests.helpers import trade, ts


class L2WhaleTest(unittest.TestCase):
    def test_large_print_detector_uses_prior_window(self):
        detector = LargePrintDetector(window=10, z_threshold=2.0)
        for i in range(6):
            self.assertIsNone(detector.update(trade(second=i, price=100.0, size=1.0)))

        event = detector.update(trade(second=7, price=100.0, size=10.0, side="BUY"))

        self.assertIsNotNone(event)
        self.assertEqual(event.side, "BUY")

    def test_spoofing_detects_fast_large_wall_cancel(self):
        detector = SpoofingDetector(min_notional=1_000.0, lifetime_ms=2_000)
        detector.update(ts_event=ts(0), bids=[(99.0, 20.0)], asks=[(101.0, 1.0)])

        events = detector.update(ts_event=ts(1), bids=[(99.0, 1.0)], asks=[(101.0, 1.0)])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].side, "BID")

    def test_iceberg_detects_refills(self):
        detector = IcebergDetector(min_refills=2, refill_tolerance=0.1)
        detector.update(bids=[(99.0, 10.0)], asks=[(101.0, 10.0)])
        detector.update(bids=[(99.0, 14.0)], asks=[(101.0, 10.0)])
        events = detector.update(bids=[(99.0, 20.0)], asks=[(101.0, 10.0)])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].side, "BID")

    def test_whale_pressure_combines_sources(self):
        large = LargePrintDetector(window=10, z_threshold=2.0)
        event = None
        for i in range(6):
            large.update(trade(second=i, price=100.0, size=1.0))
        event = large.update(trade(second=7, price=100.0, size=10.0, side="BUY"))

        pressure = WhalePressureEngine().compute(large_print=event, book_imbalance=0.5)

        self.assertGreater(pressure.pressure, 0.0)
        self.assertIn("LARGE_PRINT", pressure.reason_codes)


if __name__ == "__main__":
    unittest.main()
