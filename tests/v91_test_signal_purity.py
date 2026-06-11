import unittest

from research.v91_signal_purity import historical_flat_thresholds


class SignalPurityTests(unittest.TestCase):
    def test_historical_threshold_excludes_current_and_future_values(self):
        baseline = historical_flat_thresholds([1.0, 2.0, 3.0, 4.0], min_samples=2)
        changed_future = historical_flat_thresholds([1.0, 2.0, 3000.0, 4000.0], min_samples=2)
        self.assertEqual(baseline[:3], changed_future[:3])

    def test_historical_threshold_uses_only_prior_values(self):
        thresholds = historical_flat_thresholds(
            [1.0, 2.0, 100.0],
            quantile=0.25,
            min_samples=2,
        )
        self.assertEqual(thresholds, [0.0, 0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
