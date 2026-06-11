import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v91_features import build_extended_feature_ledger


class FeatureManifestHashTests(unittest.TestCase):
    def test_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.0 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=1.0, cumulative_delta=float(i), ticks=1) for i in range(5)]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            _, first = build_extended_feature_ledger(path)
            _, second = build_extended_feature_ledger(path)
            self.assertEqual(first["feature_hash"], second["feature_hash"])


if __name__ == "__main__":
    unittest.main()

