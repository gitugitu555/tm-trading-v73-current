import unittest

from research.validation import monte_carlo_trade_bootstrap, promote_shadow_gate, walk_forward_splits


class ValidationTests(unittest.TestCase):
    def test_walk_forward_splits(self) -> None:
        folds = walk_forward_splits(list(range(10)), train_size=4, test_size=2, step_size=2)
        self.assertEqual(len(folds), 3)
        self.assertEqual(folds[0].train_start, 0)
        self.assertEqual(folds[0].test_start, 4)

    def test_bootstrap_summary(self) -> None:
        summary = monte_carlo_trade_bootstrap([0.1, -0.05, 0.2], n_samples=200, block_size=2)
        self.assertGreaterEqual(summary.p95, summary.p05)
        self.assertGreaterEqual(summary.max_value, summary.min_value)

    def test_promotion_verdict(self) -> None:
        verdict = promote_shadow_gate(
            baseline_expectancy=1.0,
            candidate_expectancy=1.08,
            baseline_sharpe=2.0,
            candidate_sharpe=2.15,
            baseline_drawdown=10.0,
            candidate_drawdown=9.5,
            baseline_trade_count=100,
            candidate_trade_count=70,
            blocked_winners=10,
            blocked_losers=20,
        )
        self.assertTrue(verdict.eligible)
        self.assertIn("retention", verdict.metrics)


if __name__ == "__main__":
    unittest.main()
