import json
import tempfile
import unittest
from pathlib import Path

from research.trade_path_db import TradePathDatabase


class TradePathDbTests(unittest.TestCase):
    def test_trade_path_summary_and_export(self) -> None:
        db = TradePathDatabase()
        db.add_from_trade_dict(
            {
                "signal_id": "s1",
                "entry_ts_ns": 1_000_000_000,
                "exit_ts_ns": 4_600_000_000,
                "entry_price": 100.0,
                "exit_price": 101.0,
                "pnl": 1.0,
                "return_pct": 0.01,
                "side": 1,
                "exit_reason": "TARGET",
                "max_adverse": 0.01,
                "max_favorable": 0.03,
                "bars_held": 4,
                "target_pct": 0.02,
                "stop_pct": 0.01,
            }
        )
        summary = db.summary()
        self.assertEqual(summary.n_trades, 1)
        self.assertEqual(summary.n_wins, 1)
        self.assertIn("TARGET", summary.by_exit_reason)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "paths.jsonl"
            db.export_jsonl(out)
            line = out.read_text(encoding="utf-8").strip().splitlines()[0]
            payload = json.loads(line)
            self.assertEqual(payload["signal_id"], "s1")
            self.assertEqual(payload["session_hour_utc"], 0)


if __name__ == "__main__":
    unittest.main()
