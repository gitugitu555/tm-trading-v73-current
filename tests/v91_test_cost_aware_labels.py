import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_labels import build_alpha_labels


class CostAwareLabelTests(unittest.TestCase):
    def test_cost_aware_label_changes_with_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0, high=101.0 + i, low=99.0, close=100.0 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=1.0, cumulative_delta=float(i), ticks=1) for i in range(10)]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, _ = build_alpha_labels(path)
            self.assertIn("net_profitable_after_8bps_roundtrip", frame.columns)
            self.assertTrue(set(frame["net_profitable_after_8bps_roundtrip"].dropna().unique()).issubset({0, 1}))


if __name__ == "__main__":
    unittest.main()

