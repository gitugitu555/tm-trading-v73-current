import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v90_feature_ledger import build_feature_ledger


class FeatureLedgerLookaheadTests(unittest.TestCase):
    def test_first_row_has_zero_rolling_lookahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [
                VolumeBar(start_ts_ns=0, end_ts_ns=1, open=100.0, high=101.0, low=99.0, close=100.0, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=0.0, cumulative_delta=0.0, ticks=1),
                VolumeBar(start_ts_ns=1, end_ts_ns=2, open=100.0, high=102.0, low=99.0, close=101.0, volume=10.0, buy_volume=6.0, sell_volume=4.0, delta=2.0, cumulative_delta=2.0, ticks=1),
            ]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, manifest = build_feature_ledger(path)
            self.assertEqual(frame.iloc[0]["cvd_slope"], 0.0)
            self.assertEqual(manifest["row_count"], 2)


if __name__ == "__main__":
    unittest.main()

