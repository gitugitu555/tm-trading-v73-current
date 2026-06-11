import unittest
from prime.volume_bars import VolumeBar
from research.v88_signal_ledger import deterministic_signal_id

class SignalLedgerDeterminismTests(unittest.TestCase):
    def test_signal_id_is_deterministic(self):
        bar = VolumeBar(1, 2, 10, 11, 9, 10, 300, 150, 150, 0, 5, 10)
        self.assertEqual(deterministic_signal_id(bar, 1, 30, "x"), deterministic_signal_id(bar, 1, 30, "x"))
