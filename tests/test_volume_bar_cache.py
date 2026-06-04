import tempfile
import unittest
from pathlib import Path

from prime.volume_bar_cache import load_cached_bars, write_cached_bars
from prime.volume_bars import VolumeBar


class VolumeBarCacheTest(unittest.TestCase):
    def test_round_trip_preserves_cached_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "BTCUSDT-aggTrades-2022-01.zip"
            archive.write_bytes(b"raw archive placeholder")

            bars_by_threshold = {
                100.0: [
                    VolumeBar(
                        start_ts_ns=1,
                        end_ts_ns=2,
                        open=100.0,
                        high=101.0,
                        low=99.5,
                        close=100.5,
                        volume=100.0,
                        buy_volume=60.0,
                        sell_volume=40.0,
                        delta=20.0,
                        cumulative_delta=20.0,
                        ticks=12,
                    )
                ],
                200.0: [
                    VolumeBar(
                        start_ts_ns=3,
                        end_ts_ns=4,
                        open=200.0,
                        high=201.0,
                        low=199.0,
                        close=200.5,
                        volume=200.0,
                        buy_volume=120.0,
                        sell_volume=80.0,
                        delta=40.0,
                        cumulative_delta=60.0,
                        ticks=20,
                    )
                ],
            }

            cache_dir = tmp_path / "cache"
            path = write_cached_bars(cache_dir, archive, [100.0, 200.0], 12345, bars_by_threshold)
            self.assertIsNotNone(path)
            cached = load_cached_bars(cache_dir, archive, [100.0, 200.0])
            self.assertIsNotNone(cached)
            self.assertEqual(cached["rows_seen"], 12345)
            self.assertEqual(cached["bars_by_threshold"][100.0][0].close, 100.5)
            self.assertEqual(cached["bars_by_threshold"][200.0][0].delta, 40.0)

    def test_cache_invalidates_when_archive_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "BTCUSDT-aggTrades-2022-01.zip"
            archive.write_bytes(b"raw archive placeholder")
            cache_dir = tmp_path / "cache"
            bars_by_threshold = {
                100.0: [
                    VolumeBar(
                        start_ts_ns=1,
                        end_ts_ns=2,
                        open=1.0,
                        high=1.0,
                        low=1.0,
                        close=1.0,
                        volume=1.0,
                        buy_volume=1.0,
                        sell_volume=0.0,
                        delta=1.0,
                        cumulative_delta=1.0,
                        ticks=1,
                    )
                ]
            }

            write_cached_bars(cache_dir, archive, [100.0], 1, bars_by_threshold)
            archive.write_bytes(b"modified archive content")

            self.assertIsNone(load_cached_bars(cache_dir, archive, [100.0]))


if __name__ == "__main__":
    unittest.main()
