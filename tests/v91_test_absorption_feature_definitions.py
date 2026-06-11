import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_features import build_extended_feature_ledger


class AbsorptionFeatureDefinitionTests(unittest.TestCase):
    def test_absorption_proxy_detects_failed_impulse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [
                VolumeBar(start_ts_ns=0, end_ts_ns=1, open=100.0, high=101.0, low=99.0, close=100.0, volume=10.0, buy_volume=8.0, sell_volume=2.0, delta=6.0, cumulative_delta=6.0, ticks=1),
                VolumeBar(start_ts_ns=1, end_ts_ns=2, open=100.0, high=100.5, low=98.0, close=98.5, volume=10.0, buy_volume=9.0, sell_volume=1.0, delta=8.0, cumulative_delta=14.0, ticks=1),
            ]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, _ = build_extended_feature_ledger(path)
            self.assertGreaterEqual(frame.iloc[1]["positive_delta_negative_return"], 1)
            self.assertGreaterEqual(frame.iloc[1]["absorption_score"], 1.0)


if __name__ == "__main__":
    unittest.main()

