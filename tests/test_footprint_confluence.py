"""Footprint confluence filter tests."""

from __future__ import annotations

import unittest

from prime.footprint_confluence import footprint_confirms_fade


class FootprintConfluenceTests(unittest.TestCase):
    def test_neutral_bias_passes(self) -> None:
        self.assertTrue(footprint_confirms_fade(trade_side=-1, footprint_bias=0, footprint_stacked=False))

    def test_aligned_bias_passes(self) -> None:
        self.assertTrue(footprint_confirms_fade(trade_side=-1, footprint_bias=-1, footprint_stacked=True))

    def test_opposing_bias_fails(self) -> None:
        self.assertFalse(footprint_confirms_fade(trade_side=-1, footprint_bias=1, footprint_stacked=True))


if __name__ == "__main__":
    unittest.main()