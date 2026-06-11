import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from prime.volume_bars import VolumeBar
from research.v89_volume_bar_builder import load_verified_catalog
from research.v91_features import build_extended_feature_ledger
from research.v91_scan import build_candidate_signals
from research.v91_replay import replay_candidates


class CandidateReplayAccountingTests(unittest.TestCase):
    def test_candidate_replay_produces_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.parquet"
            bars = [
                VolumeBar(start_ts_ns=i, end_ts_ns=i + 1, open=100.0 + i, high=101.0 + i, low=99.0, close=100.5 + i, volume=10.0, buy_volume=5.0, sell_volume=5.0, delta=float(i + 1), cumulative_delta=float(i), ticks=1)
                for i in range(120)
            ]
            pq.write_table(pa.Table.from_pylist([asdict(bar) for bar in bars]), path)
            features, _ = build_extended_feature_ledger(path)
            signals = build_candidate_signals(features, lambda df: df.index == 0, side=1)
            replay = replay_candidates(bars, signals, {"name": "demo", "target_pct": 0.005, "stop_pct": 0.03, "bar_exit": 24, "trail_start_mfe_pct": 0.002, "trail_giveback_pct": 0.25})
            self.assertIn("summary", replay)
            self.assertIn("trades", replay)


if __name__ == "__main__":
    unittest.main()

