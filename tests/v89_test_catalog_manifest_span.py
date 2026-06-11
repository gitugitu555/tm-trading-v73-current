import unittest
from research.v89_volume_bar_builder import build_manifest
from prime.volume_bars import VolumeBar
from pathlib import Path

class ManifestSpanTests(unittest.TestCase):
    def test_manifest_uses_content_span(self):
        bars=[VolumeBar(1,2,1,1,1,1,300,0,0,0,0,1)]
        manifest=build_manifest(bars=bars,trade_count=1,raw_manifest_hash="r",coverage_audit_hash="c",output_file=Path("x"),repo_commit="g")
        self.assertEqual(manifest["start_ts_ns"],1)
        self.assertEqual(manifest["end_ts_ns"],2)
