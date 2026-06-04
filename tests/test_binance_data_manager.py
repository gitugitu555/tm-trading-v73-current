import unittest
from pathlib import Path

from storage.dataset_layout import DatasetSpec, binance_dataset_spec, dataset_path


class BinanceDatasetLayoutTest(unittest.TestCase):
    def test_binance_spec_builds_canonical_relative_path(self):
        spec = binance_dataset_spec(
            market="spot",
            kind="aggTrades",
            symbol="BTCUSDT",
            range_label="2020-05-22_to_2026-05-21",
        )

        self.assertEqual(
            spec.relative_path(),
            Path("binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"),
        )

    def test_dataset_path_joins_root_and_relative_path(self):
        spec = DatasetSpec(
            exchange="binance",
            market="futures",
            kind="aggTrades",
            symbol="ETHUSDT",
            range_label="2024-01-01_to_2024-12-31",
        )

        self.assertEqual(
            dataset_path(Path("/mnt/seagate/tm-trading-v555/data/raw"), spec),
            Path("/mnt/seagate/tm-trading-v555/data/raw/binance/futures/aggTrades/ETHUSDT/2024-01-01_to_2024-12-31"),
        )


if __name__ == "__main__":
    unittest.main()

