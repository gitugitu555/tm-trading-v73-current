"""Parity tests for shared volume-bar CVD signal engine."""

from __future__ import annotations

import unittest

from prime.volume_bar_cvd import htf_flat_abs_threshold, volume_bar_cvd_signal
from prime.volume_bars import VolumeBar


def _bar(
    end_ts: int,
    *,
    high: float,
    low: float,
    cvd: float,
) -> VolumeBar:
    return VolumeBar(
        start_ts_ns=end_ts - 1,
        end_ts_ns=end_ts,
        open=high,
        high=high,
        low=low,
        close=(high + low) / 2,
        volume=300.0,
        buy_volume=150.0,
        sell_volume=150.0,
        delta=0.0,
        cumulative_delta=cvd,
        ticks=10,
    )


class VolumeBarCVDEngineTests(unittest.TestCase):
    def test_bearish_divergence_with_htf_filter(self) -> None:
        bars = [
            _bar(i, high=100.0, low=99.0, cvd=float(i)) for i in range(1, 42)
        ]
        bars[-1] = _bar(42, high=105.0, low=104.0, cvd=10.0)
        flat_abs = htf_flat_abs_threshold([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])
        signal = volume_bar_cvd_signal(
            bars,
            lookback_bars=40,
            htf_change=0.0,
            flat_abs=flat_abs,
            timestamp_ns=42,
            price=104.5,
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], -1)

    def test_htf_blocks_bearish_when_hour_trending_up(self) -> None:
        bars = [
            _bar(i, high=100.0, low=99.0, cvd=float(i)) for i in range(1, 42)
        ]
        bars[-1] = _bar(42, high=105.0, low=104.0, cvd=10.0)
        signal = volume_bar_cvd_signal(
            bars,
            lookback_bars=40,
            htf_change=50.0,
            flat_abs=5.0,
            timestamp_ns=42,
            price=104.5,
        )
        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()