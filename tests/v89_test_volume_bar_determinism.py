import unittest
from prime.volume_bars import VolumeBar
from research.v89_volume_bar_builder import bars_hash

class BarDeterminismTests(unittest.TestCase):
    def test_hash_deterministic(self):
        bars=[VolumeBar(1,2,1,2,1,2,300,150,150,0,0,1)]
        self.assertEqual(bars_hash(bars),bars_hash(bars))
