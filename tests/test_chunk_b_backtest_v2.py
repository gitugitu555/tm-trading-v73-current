import unittest

from prime.chunk_b_backtest import ChunkBBacktester as V1Backtester
from prime.chunk_b_backtest_v2 import ChunkBBacktester as V2Backtester
from prime.chunk_b_backtest_v2 import OpenTradeState


class ChunkBBacktestV2Test(unittest.TestCase):
    def test_v2_entrypoint_uses_current_typed_backtester(self) -> None:
        self.assertIs(V2Backtester, V1Backtester)
        self.assertTrue(hasattr(OpenTradeState, "with_excursion"))


if __name__ == "__main__":
    unittest.main()
