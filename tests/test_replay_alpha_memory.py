import csv
import json
import tempfile
import unittest
from pathlib import Path

from core.types import FeatureSnapshot
from data.replay.validator import ReplayValidator
from memory.setup_summary import build_setup_memory_object
from strategy.alpha_permission import AlphaPermissionEngine
from tests.helpers import ts


class ReplayAlphaMemoryTest(unittest.TestCase):
    def test_replay_csv_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            trades = Path(tmp) / "trades.csv"
            books = Path(tmp) / "books.csv"
            with trades.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "ts_event",
                        "exchange",
                        "symbol",
                        "price",
                        "size_base",
                        "buyer_is_maker",
                        "trade_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ts_event": "2026-05-21T09:30:00Z",
                        "exchange": "BINANCE",
                        "symbol": "BTCUSDT",
                        "price": "100",
                        "size_base": "1",
                        "buyer_is_maker": "false",
                        "trade_id": "1",
                    }
                )
                writer.writerow(
                    {
                        "ts_event": "2026-05-21T09:30:01Z",
                        "exchange": "BINANCE",
                        "symbol": "BTCUSDT",
                        "price": "99",
                        "size_base": "2",
                        "buyer_is_maker": "true",
                        "trade_id": "2",
                    }
                )
            with books.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["ts_event", "exchange", "symbol", "bids", "asks"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "ts_event": "2026-05-21T09:30:00Z",
                        "exchange": "BINANCE",
                        "symbol": "BTCUSDT",
                        "bids": json.dumps([[99.0, 10.0]]),
                        "asks": json.dumps([[101.0, 2.0]]),
                    }
                )

            validator = ReplayValidator(tick_size=0.1)
            snapshots_a, report_a = validator.replay_csv(trades_csv=trades, books_csv=books)
            snapshots_b, report_b = validator.replay_csv(trades_csv=trades, books_csv=books)

            self.assertEqual(report_a.checksum, report_b.checksum)
            self.assertTrue(report_a.parity_passed)
            self.assertEqual(len(snapshots_a), 2)
            self.assertEqual(snapshots_a, snapshots_b)

    def test_alpha_permission_reason_codes(self):
        snapshot = FeatureSnapshot(
            ts_event=ts(),
            instrument="BTCUSDT",
            delta_velocity=10.0,
            delta_acceleration=5.0,
            book_imbalance=0.5,
            whale_pressure=20.0,
        )

        permission = AlphaPermissionEngine().compute(snapshot)

        self.assertEqual(permission.direction, 1)
        self.assertTrue(permission.allow_trade)
        self.assertIn("CVD_VELOCITY_UP", permission.reason_codes)

    def test_memory_export_is_json_ready(self):
        snapshot = FeatureSnapshot(ts_event=ts(), instrument="BTCUSDT", delta_velocity=1.0)

        memory = build_setup_memory_object(
            snapshot=snapshot,
            setup_type="semantic_pattern_recall",
        )

        self.assertEqual(memory.to_json_ready()["instrument"], "BTCUSDT")
        self.assertIn("semantic_pattern_recall", memory.summary)


if __name__ == "__main__":
    unittest.main()
