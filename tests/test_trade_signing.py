import unittest

from features.trade_signing import TradeSigner, bvc_classify
from tests.helpers import ts


class TradeSigningTest(unittest.TestCase):
    def test_binance_buyer_is_maker_rule(self):
        signer = TradeSigner()

        sell = signer.sign(
            ts_event=ts(),
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=100.0,
            size_base=2.0,
            buyer_is_maker=True,
        )
        buy = signer.sign(
            ts_event=ts(1),
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=101.0,
            size_base=1.0,
            buyer_is_maker=False,
        )

        self.assertEqual(sell.side, "SELL")
        self.assertEqual(buy.side, "BUY")
        self.assertEqual(sell.method, "binance_buyer_is_maker")

    def test_lee_ready_then_tick_fallback(self):
        signer = TradeSigner()

        first = signer.sign(
            ts_event=ts(),
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=101.0,
            size_base=1.0,
            mid_before=100.0,
        )
        second = signer.sign(
            ts_event=ts(1),
            exchange="BINANCE",
            symbol="BTCUSDT",
            price=100.5,
            size_base=1.0,
        )

        self.assertEqual(first.side, "BUY")
        self.assertEqual(second.side, "SELL")
        self.assertEqual(second.method, "tick_rule")

    def test_bvc_mid_split(self):
        self.assertEqual(
            bvc_classify(100.0, 100.0, 10.0),
            {"buy_volume": 5.0, "sell_volume": 5.0, "confidence": 0.4},
        )


if __name__ == "__main__":
    unittest.main()
