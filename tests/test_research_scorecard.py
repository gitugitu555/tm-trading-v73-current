"""Tests for research manifests and signal scorecard."""

from __future__ import annotations

import unittest

from research.manifests import config_hash, wrap_result_payload
from research.signal_scorecard import SignalEvent, SignalScorecard


class ResearchScorecardTests(unittest.TestCase):
    def test_signal_scorecard_hit_rate(self) -> None:
        card = SignalScorecard(horizon_bars=2)
        closes = [100.0, 100.0, 101.0, 102.0, 103.0]
        card.add(
            SignalEvent(
                bar_index=0,
                timestamp_ns=1,
                side=1,
                entry_price=100.0,
                signal_id="t",
                permission_verdict="APPROVE",
            )
        )
        card.add(
            SignalEvent(
                bar_index=1,
                timestamp_ns=2,
                side=-1,
                entry_price=100.0,
                signal_id="t2",
                permission_verdict="APPROVE",
            )
        )
        out = card.finalize(closes)
        self.assertEqual(out["scored_events"], 2)
        self.assertGreater(out["hit_rate"], 0.0)

    def test_wrap_result_payload_adds_manifests(self) -> None:
        payload = {
            "archive": "BTCUSDT-aggTrades-2022-09.zip",
            "strategy": "volume_bar_cvd",
            "report": {
                "win_rate": 0.4,
                "trades": 10,
                "config": {"divergence_type": "volume_bar_cvd"},
                "signal_scorecard": {"hit_rate": 0.53, "events": 100},
            },
        }
        wrapped = wrap_result_payload(
            payload,
            experiment_id="test",
            command="unittest",
            output_path="results/test.json",
        )
        self.assertIn("experiment_manifest", wrapped)
        self.assertIn("result_manifest", wrapped)
        self.assertEqual(wrapped["result_manifest"]["trade_win_rate"], 0.4)
        self.assertEqual(wrapped["result_manifest"]["signal_win_rate"], 0.53)

    def test_config_hash_stable(self) -> None:
        a = config_hash({"a": 1, "b": 2})
        b = config_hash({"b": 2, "a": 1})
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()