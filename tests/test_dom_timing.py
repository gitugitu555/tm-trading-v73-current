import unittest
from datetime import datetime, timezone

from core.types import BookSnapshot
from execution.dom_timing import analyze_dom_timing


class DOMTimingTests(unittest.TestCase):
    def test_fill_probability_and_costs_are_bounded(self) -> None:
        book = BookSnapshot(
            ts_event=datetime(2026, 6, 9, tzinfo=timezone.utc),
            exchange="binance",
            symbol="BTCUSDT",
            bids=((100.0, 10.0), (99.5, 8.0), (99.0, 6.0), (98.5, 4.0), (98.0, 2.0)),
            asks=((100.5, 2.0), (101.0, 3.0), (101.5, 4.0), (102.0, 5.0), (102.5, 6.0)),
        )
        snap = analyze_dom_timing(book, side=1, order_size=1.5, latency_ms=20.0)
        self.assertGreaterEqual(snap.fill_probability, 0.0)
        self.assertLessEqual(snap.fill_probability, 1.0)
        self.assertGreater(snap.spread_bps, 0.0)
        self.assertGreater(snap.execution_quality_score, 0.0)

    def test_short_and_long_use_opposite_effective_prices(self) -> None:
        book = BookSnapshot(
            ts_event=datetime(2026, 6, 9, tzinfo=timezone.utc),
            exchange="binance",
            symbol="BTCUSDT",
            bids=((100.0, 10.0), (99.5, 8.0), (99.0, 6.0), (98.5, 4.0), (98.0, 2.0)),
            asks=((100.5, 2.0), (101.0, 3.0), (101.5, 4.0), (102.0, 5.0), (102.5, 6.0)),
        )
        long_snap = analyze_dom_timing(book, side=1, order_size=1.0)
        short_snap = analyze_dom_timing(book, side=-1, order_size=1.0)
        self.assertGreater(long_snap.effective_entry_price, book.best_ask)
        self.assertLess(short_snap.effective_entry_price, book.best_bid)


if __name__ == "__main__":
    unittest.main()
