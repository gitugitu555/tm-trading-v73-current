import unittest
from datetime import datetime, timezone
from core.types import BookSnapshot
from execution.realism import ExecutionRealismEngine, ExecutionRealismResult

class ExecutionRealismTests(unittest.TestCase):
    def test_execution_realism_calculation(self) -> None:
        book = BookSnapshot(
            ts_event=datetime.now(timezone.utc),
            exchange="BINANCE",
            symbol="BTCUSDT",
            bids=((100.0, 10.0), (99.9, 5.0)),
            asks=((100.1, 2.0), (100.2, 8.0)),
        )

        engine = ExecutionRealismEngine(base_latency_ms=25.0)

        # Long entry test
        res_long = engine.estimate_realism(
            book=book,
            side=1,
            original_price=100.1,
            order_size=1.0,
            additional_latency_ms=5.0
        )
        self.assertEqual(res_long.lag_ms, 30.0)
        self.assertGreater(res_long.slippage_bps, 0.0)
        self.assertGreater(res_long.illusion_tax_bps, 0.0)
        self.assertGreater(res_long.effective_price, 100.1)

        # Short entry test
        res_short = engine.estimate_realism(
            book=book,
            side=-1,
            original_price=100.0,
            order_size=1.0
        )
        self.assertEqual(res_short.lag_ms, 25.0)
        self.assertLess(res_short.effective_price, 100.0)

    def test_invalid_arguments_raise_error(self) -> None:
        book = BookSnapshot(
            ts_event=datetime.now(timezone.utc),
            exchange="BINANCE",
            symbol="BTCUSDT",
            bids=((100.0, 10.0),),
            asks=((100.1, 2.0),),
        )
        engine = ExecutionRealismEngine()
        with self.assertRaises(ValueError):
            engine.estimate_realism(book, 0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            engine.estimate_realism(book, 1, 100.0, -1.0)

if __name__ == "__main__":
    unittest.main()
