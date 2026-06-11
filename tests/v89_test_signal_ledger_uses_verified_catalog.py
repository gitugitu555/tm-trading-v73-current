import unittest
from prime.volume_bars import VolumeBar
from research.v88_signal_ledger import deterministic_signal_id

class VerifiedLedgerTests(unittest.TestCase):
    def test_manifest_hash_changes_signal_id(self):
        bar=VolumeBar(1,2,1,1,1,1,300,0,0,0,0,1)
        self.assertNotEqual(deterministic_signal_id(bar,1,30,"a"),deterministic_signal_id(bar,1,30,"b"))
