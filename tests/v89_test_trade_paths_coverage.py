import unittest
from prime.volume_bars import VolumeBar
from research.v88_trade_path import reconstruct_path

class PathCoverageTests(unittest.TestCase):
    def test_incomplete_end_path_is_explicit(self):
        bars=[VolumeBar(1,2,1,1,1,1,300,0,0,0,0,1)]
        path=reconstruct_path({"signal_id":"x","bar_id":0,"signal_ts_ns":2,"side":"long","side_int":1,"entry_reference_price":1},bars)
        self.assertEqual(path["forward_bars"],0)
