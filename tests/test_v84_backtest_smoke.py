from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
SCRIPT = ROOT / "scripts/chunk_b_backtest_cached.py"
DEST = ROOT / "data/raw/binance/spot/aggTrades/BTCUSDT/2020-05-22_to_2026-05-21"


class V84BacktestSmokeTest(unittest.TestCase):
    def test_new_shadow_gates_emit_report_fields(self) -> None:
        proc = subprocess.run(
            [
                str(PYTHON),
                str(SCRIPT),
                "--dest",
                str(DEST),
                "--archive",
                "BTCUSDT-aggTrades-2020-05-22.zip",
                "--threshold-btc",
                "300",
                "--signal-mode",
                "divergence",
                "--divergence-type",
                "volume_bar_cvd",
                "--no-use-time-exit",
                "--exit-after-volume-bars",
                "16",
                "--entry-lag-bars",
                "1",
                "--use-vpin-gate",
                "--use-market-profile-gate",
                "--use-anti-pattern-gate",
                "--use-risk-state-gate",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("Running backtest over cached bars", proc.stdout)
        text = proc.stdout.strip()
        start = text.find("{")
        self.assertGreaterEqual(start, 0, msg=proc.stdout)
        payload = json.loads(text[start:])
        report = payload["report"]
        self.assertIn("market_profile", report)
        self.assertIn("mlofi_snapshot", report)
        self.assertIn("shadow_gate_counts", report)
        self.assertIn("profile_type", report["market_profile"])
        self.assertIn("mlofi_zscore", report["mlofi_snapshot"])
        self.assertIn("anti_pattern_block", report["shadow_gate_counts"])


if __name__ == "__main__":
    unittest.main()
