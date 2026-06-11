import unittest

import pandas as pd

from research.v91_scan import monthly_rank_ic


class UnivariateScanTests(unittest.TestCase):
    def test_monthly_rank_ic_uses_month_buckets(self):
        feature_frame = pd.DataFrame({"month": ["2020-01", "2020-01", "2020-02", "2020-02"], "feature": [1.0, 2.0, 3.0, 4.0]})
        labels = pd.DataFrame({"target": [0.1, 0.2, 0.3, 0.4]})
        report = monthly_rank_ic(feature_frame, labels, "feature", "target")
        self.assertEqual(report["feature"], "feature")
        self.assertEqual(report["label"], "target")
        self.assertIn("deciles", report)


if __name__ == "__main__":
    unittest.main()

