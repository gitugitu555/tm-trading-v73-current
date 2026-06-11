import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v90_labels import build_labels


class LabelGenerationTests(unittest.TestCase):
    def test_triple_barrier_columns_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [
                VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.5 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=0.0, cumulative_delta=float(i), ticks=1)
                for i in range(6)
            ]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, manifest = build_labels(path)
            self.assertIn("future_return_8_bars", frame.columns)
            self.assertIn("triple_barrier_0.002_0.002_24", frame.columns)
            self.assertEqual(manifest["row_count"], 6)


if __name__ == "__main__":
    unittest.main()

