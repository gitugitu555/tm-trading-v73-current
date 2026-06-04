import unittest
from collections import deque
from prime.chunk_b_backtest import ChunkBBacktestConfig, ChunkBBacktester
from prime.nautilus_compat import TradeTick, InstrumentId, Price, Quantity, AggressorSide

class VolumeBarCVDSignalTest(unittest.TestCase):
    def test_volume_bar_cvd_signal_initialization_and_evaluation(self) -> None:
        config = ChunkBBacktestConfig(
            signal_mode="divergence",
            divergence_type="volume_bar_cvd",
            volume_bar_threshold=10.0,
            divergence_lookback_bars=2,
            htf_flat_quantile=0.25,
        )
        backtester = ChunkBBacktester(config)
        
        # Verify custom configs exist
        self.assertEqual(backtester.config.volume_bar_threshold, 10.0)
        self.assertEqual(backtester.config.divergence_lookback_bars, 2)
        
        # Generate ticks to form bars
        instrument = InstrumentId.from_str("BTCUSDT.BINANCE")
        ticks = []
        
        # We need 3 bars of size 10 BTC:
        # Bar 1: Price goes from 100 to 101, Volume 10 (all buys) -> cumulative CVD increases
        for i in range(10):
            ticks.append(TradeTick(
                instrument_id=instrument,
                price=Price(100.0 + i * 0.1, precision=2),
                size=Quantity(1.0, precision=8),
                aggressor_side=AggressorSide.BUYER,
                trade_id=str(i),
                ts_event=1000 + i * 1000,
                ts_init=1000 + i * 1000,
            ))
            
        # Bar 2: Price goes from 101 to 102, Volume 10 (all buys)
        for i in range(10):
            ticks.append(TradeTick(
                instrument_id=instrument,
                price=Price(101.0 + i * 0.1, precision=2),
                size=Quantity(1.0, precision=8),
                aggressor_side=AggressorSide.BUYER,
                trade_id=str(10 + i),
                ts_event=20000 + i * 1000,
                ts_init=20000 + i * 1000,
            ))

        # Bar 3: Price goes to 103 (high >= prior high), but CVD decreases (sells)
        # Price goes to 103.0, volume 10 (all sells) -> bearish divergence
        for i in range(10):
            ticks.append(TradeTick(
                instrument_id=instrument,
                price=Price(103.0 - i * 0.05, precision=2),
                size=Quantity(1.0, precision=8),
                aggressor_side=AggressorSide.SELLER,
                trade_id=str(20 + i),
                ts_event=40000 + i * 1000,
                ts_init=40000 + i * 1000,
            ))

        report, trades = backtester.run(ticks)
        
        # Verify bars are saved in backtester history
        self.assertEqual(len(backtester._bars), 3)
        self.assertEqual(backtester._bars[0].volume, 10.0)
        self.assertEqual(backtester._bars[1].volume, 10.0)
        self.assertEqual(backtester._bars[2].volume, 10.0)

if __name__ == "__main__":
    unittest.main()
