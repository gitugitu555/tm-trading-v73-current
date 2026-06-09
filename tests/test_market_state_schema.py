import unittest
from schema.market_state import BookSnapshot, MarketStateFrame, ShadowGateResult

class MarketStateSchemaTests(unittest.TestCase):
    def test_book_snapshot_instantiation(self) -> None:
        snap = BookSnapshot(
            ts_ns=1718000000000,
            symbol="BTCUSDT",
            venue="BINANCE",
            bid_px=[100.0, 99.9],
            bid_sz=[1.0, 2.0],
            ask_px=[100.1, 100.2],
            ask_sz=[1.5, 0.5]
        )
        self.assertEqual(snap.symbol, "BTCUSDT")
        self.assertEqual(snap.venue, "BINANCE")
        self.assertEqual(snap.bid_px[0], 100.0)

    def test_market_state_frame_instantiation(self) -> None:
        frame = MarketStateFrame(
            ts_ns=1718000000000,
            symbol="BTCUSDT",
            side_candidate="BUY",
            cvd=125.5,
            cvd_divergence_score=0.85,
            microprice_drift_bps=2.1,
            mlofi_w=0.45,
            mlofi_depth_scaled=0.12,
            queue_imbalance_top5=0.33,
            vpin_score=0.67,
            toxicity_state="NORMAL",
            atr_used_pct=34.2,
            profile_context="VALUE_AREA",
            distance_to_poc_bps=12.0,
            dom_entry_quality=0.9,
            risk_state="NORMAL"
        )
        self.assertEqual(frame.side_candidate, "BUY")
        self.assertEqual(frame.cvd, 125.5)

    def test_shadow_gate_result_instantiation(self) -> None:
        res = ShadowGateResult(
            gate_id="vpin_gate",
            passed=True,
            score=0.67,
            reason=None,
            would_block=False
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.would_block)

if __name__ == "__main__":
    unittest.main()
