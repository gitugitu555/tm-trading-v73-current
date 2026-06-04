import unittest

from prime.auction_state import AuctionStateEngine


class AuctionStateEngineTest(unittest.TestCase):
    def test_balanced_to_discovery_with_hysteresis(self) -> None:
        engine = AuctionStateEngine(hysteresis_bars=2)

        first = engine.update(
            timestamp_ns=1,
            price_change_5m_pct=0.0016,
            cvd_session=20.0,
            value_acceptance=False,
        )
        second = engine.update(
            timestamp_ns=2,
            price_change_5m_pct=0.0017,
            cvd_session=25.0,
            value_acceptance=False,
        )

        self.assertEqual(first.state, "BALANCED")
        self.assertIsNone(first.transition)
        self.assertEqual(second.state, "DISCOVERY")
        self.assertEqual(second.transition, "BALANCED->DISCOVERY")

    def test_discovery_to_trending_requires_acceptance(self) -> None:
        engine = AuctionStateEngine(hysteresis_bars=1)

        snapshot = engine.update(
            timestamp_ns=1,
            price_change_5m_pct=0.0032,
            cvd_session=120.0,
            value_acceptance=True,
        )

        self.assertEqual(snapshot.state, "TRENDING")
        self.assertEqual(snapshot.transition, "BALANCED->TRENDING")

    def test_failed_auction_requires_extreme_flow_and_rejection(self) -> None:
        engine = AuctionStateEngine(hysteresis_bars=1)

        snapshot = engine.update(
            timestamp_ns=1,
            price_change_5m_pct=-0.005,
            cvd_session=-150.0,
            value_acceptance=False,
        )

        self.assertEqual(snapshot.state, "FAILED_AUCTION")
        self.assertEqual(snapshot.transition, "BALANCED->FAILED_AUCTION")
        self.assertGreaterEqual(snapshot.confidence, 0.8)

    def test_exhaustion_is_terminal_before_failed_auction(self) -> None:
        engine = AuctionStateEngine(hysteresis_bars=1)

        snapshot = engine.update(
            timestamp_ns=1,
            price_change_5m_pct=0.005,
            cvd_session=10.0,
            value_acceptance=True,
        )

        self.assertEqual(snapshot.state, "EXHAUSTION")
        self.assertEqual(snapshot.transition, "BALANCED->EXHAUSTION")

    def test_balanced_remains_stable_on_small_inputs(self) -> None:
        engine = AuctionStateEngine(hysteresis_bars=2)

        snapshot = engine.update(
            timestamp_ns=1,
            price_change_5m_pct=0.0002,
            cvd_session=1.0,
            value_acceptance=False,
        )

        self.assertEqual(snapshot.state, "BALANCED")
        self.assertEqual(snapshot.bars_in_state, 1)
        self.assertEqual(snapshot.transition_reason, "NO_STRONG_IMBALANCE")
