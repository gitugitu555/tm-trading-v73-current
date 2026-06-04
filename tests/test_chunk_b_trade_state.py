import unittest

from prime.chunk_b_trade_state import OpenTradeState


class OpenTradeStateTest(unittest.TestCase):
    def test_long_excursion_tracks_adverse_and_favorable_without_mutation(self) -> None:
        trade = OpenTradeState(
            entry_ts_ns=1,
            side=1,
            entry_price=100.0,
            notional=1000.0,
            signal_id="sig",
            permission_verdict="APPROVE",
            reason_codes=("TEST",),
            exit_after_ts_ns=2,
        )

        after_drawdown = trade.with_excursion(98.0)
        after_rally = after_drawdown.with_excursion(103.0)

        self.assertEqual(trade.max_adverse, 0.0)
        self.assertEqual(trade.max_favorable, 0.0)
        self.assertAlmostEqual(after_rally.max_adverse, 0.02)
        self.assertAlmostEqual(after_rally.max_favorable, 0.03)

    def test_short_excursion_tracks_adverse_and_favorable_without_mutation(self) -> None:
        trade = OpenTradeState(
            entry_ts_ns=1,
            side=-1,
            entry_price=100.0,
            notional=1000.0,
            signal_id="sig",
            permission_verdict="APPROVE",
            reason_codes=("TEST",),
            exit_after_ts_ns=2,
        )

        after_drawdown = trade.with_excursion(104.0)
        after_drop = after_drawdown.with_excursion(97.0)

        self.assertAlmostEqual(after_drop.max_adverse, 0.04)
        self.assertAlmostEqual(after_drop.max_favorable, 0.03)

    def test_legacy_dict_shape_matches_current_backtester_keys(self) -> None:
        trade = OpenTradeState(
            entry_ts_ns=1,
            side=1,
            entry_price=100.0,
            notional=1000.0,
            signal_id="sig",
            permission_verdict="APPROVE",
            reason_codes=("TEST",),
            exit_after_ts_ns=2,
            max_adverse=0.01,
            max_favorable=0.02,
        )

        self.assertEqual(
            set(trade.as_legacy_dict()),
            {
                "entry_ts_ns",
                "side",
                "entry_price",
                "notional",
                "signal_id",
                "permission_verdict",
                "reason_codes",
                "exit_after_ts_ns",
                "max_adverse",
                "max_favorable",
            },
        )

    def test_from_legacy_dict_accepts_minimal_private_helper_shape(self) -> None:
        trade = OpenTradeState.from_legacy_dict(
            {
                "side": -1,
                "entry_price": 100.0,
                "exit_after_ts_ns": 10_000,
            }
        )

        self.assertEqual(trade.side, -1)
        self.assertEqual(trade.entry_price, 100.0)
        self.assertEqual(trade.exit_after_ts_ns, 10_000)
