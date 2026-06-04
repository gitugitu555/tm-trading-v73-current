import unittest

from execution.nautilus_adapter import NoTradeNautilusStrategy
from tests.helpers import trade


class NautilusBoundaryTest(unittest.TestCase):
    def test_no_trade_strategy_emits_snapshots_without_orders(self):
        strategy = NoTradeNautilusStrategy(enable_trading=False)

        snapshot = strategy.on_trade_tick(trade(size=2.0, side="BUY"))

        self.assertEqual(snapshot.cvd, 2.0)
        self.assertEqual(len(strategy.snapshots), 1)


if __name__ == "__main__":
    unittest.main()
