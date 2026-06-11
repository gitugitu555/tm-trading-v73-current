import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_features import build_extended_feature_ledger


class ExtendedFeatureLedgerTests(unittest.TestCase):
    def test_feature_columns_and_no_lookahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [
                VolumeBar(start_ts_ns=0, end_ts_ns=1, open=100.0, high=101.0, low=99.0, close=100.0, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=0.0, cumulative_delta=0.0, ticks=1),
                VolumeBar(start_ts_ns=1, end_ts_ns=2, open=100.0, high=102.0, low=99.0, close=101.0, volume=12.0, buy_volume=7.0, sell_volume=5.0, delta=2.0, cumulative_delta=2.0, ticks=1),
                VolumeBar(start_ts_ns=2, end_ts_ns=3, open=101.0, high=103.0, low=100.0, close=102.0, volume=11.0, buy_volume=6.0, sell_volume=5.0, delta=1.0, cumulative_delta=3.0, ticks=1),
            ]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, manifest = build_extended_feature_ledger(path)
            self.assertIn("old_divergence_signal", frame.columns)
            self.assertIn("absorption_score", frame.columns)
            self.assertEqual(manifest["row_count"], 3)
            self.assertEqual(frame.iloc[0]["old_divergence_signal"], 0)


if __name__ == "__main__":
    unittest.main()

