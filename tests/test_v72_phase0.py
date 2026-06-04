import hashlib
import json
import unittest
from dataclasses import asdict

from prime.contracts import SignMethod, SignedTrade
from prime.nautilus_compat import AggressorSide, InstrumentId, Price, Quantity, TradeId, TradeTick
from prime.phase0 import DataQualityFirewall, TradeSigner


def tick(idx: int, price: float = 100.0, side=AggressorSide.BUYER) -> TradeTick:
    ts = 1_700_000_000_000_000_000 + idx * 1_000_000_000
    return TradeTick(
        instrument_id=InstrumentId.from_str("BTCUSDT.BINANCE"),
        price=Price(price, precision=2),
        size=Quantity(1.0, precision=8),
        aggressor_side=side,
        trade_id=TradeId(str(idx)),
        ts_event=ts,
        ts_init=ts,
    )


class V72Phase0Test(unittest.TestCase):
    def test_replay_determinism(self):
        ticks = [tick(0, 100.0), tick(1, 101.0, AggressorSide.SELLER), tick(2, 100.5)]
        outputs = []
        for _ in range(3):
            signer = TradeSigner(source="BINANCE", session_id="test")
            result = [signer.sign(item) for item in ticks]
            digest = hashlib.sha256(
                json.dumps([asdict(row) for row in result], default=str).encode("utf-8")
            ).hexdigest()
            outputs.append(digest)
        self.assertEqual(len(set(outputs)), 1)

    def test_unknown_sign_coverage_with_native_binance_ticks(self):
        signer = TradeSigner(source="BINANCE", session_id="test")
        trades = [signer.sign(tick(idx, side=AggressorSide.BUYER)) for idx in range(100)]
        unknown = sum(1 for trade in trades if trade.sign_method == SignMethod.UNKNOWN)
        self.assertLess(unknown / len(trades), 0.001)

    def test_crossed_book_halts(self):
        signer = TradeSigner(source="BINANCE", session_id="test")
        trade = signer.sign(tick(0))
        snap = DataQualityFirewall().check(
            trade,
            receive_ts_ns=trade.timestamp_ns,
            crossed_book=True,
        )
        self.assertEqual(snap.state, "HALT")
        self.assertIn("CROSSED_BOOK", snap.reason_codes)

    def test_firewall_no_exception_on_bad_input(self):
        fw = DataQualityFirewall()
        bad_trade = SignedTrade(
            trade_id="",
            symbol="",
            timestamp_ns=-999,
            price=0.0,
            size=0.0,
            side=0,
            sign_method=SignMethod.UNKNOWN,
            sign_confidence=0.0,
            source="",
            raw_hash="",
            session_id="",
        )
        snap = fw.check(bad_trade, receive_ts_ns=0)
        self.assertIn(snap.state, ("CLEAN", "DEGRADED", "HALT"))


if __name__ == "__main__":
    unittest.main()

