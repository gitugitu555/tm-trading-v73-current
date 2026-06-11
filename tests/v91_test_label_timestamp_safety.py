import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_labels import build_alpha_labels


class LabelTimestampSafetyTests(unittest.TestCase):
    def test_labels_are_deterministic_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.0 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=1.0, cumulative_delta=float(i), ticks=1) for i in range(8)]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            first, manifest = build_alpha_labels(path)
            second, manifest2 = build_alpha_labels(path)
            self.assertEqual(manifest["label_hash"], manifest2["label_hash"])
            self.assertEqual(first.shape[0], 8)
            self.assertIn("future_return_24", first.columns)


if __name__ == "__main__":
    unittest.main()

