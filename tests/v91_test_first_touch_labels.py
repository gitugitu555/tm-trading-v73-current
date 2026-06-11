import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_labels import build_alpha_labels


class FirstTouchLabelTests(unittest.TestCase):
    def test_first_touch_columns_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0, high=100.0 + i, low=99.0, close=100.0 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=1.0, cumulative_delta=float(i), ticks=1) for i in range(12)]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            frame, _ = build_alpha_labels(path)
            self.assertIn("touch_target_0.2_before_stop_0.2", frame.columns)
            self.assertEqual(frame.shape[0], 12)


if __name__ == "__main__":
    unittest.main()

