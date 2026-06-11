import unittest
from research.v88_capital_allocation import replay_capital

class CapitalTests(unittest.TestCase):
    def test_fixed_fractional_accounting(self):
        result = replay_capital([{"net_return_pct": .10}], starting_equity=100, base_position_pct=.5)
        self.assertEqual(result["ending_equity"], 105)
        self.assertEqual(result["raw_expectancy"], .10)
