import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from research.v90_predictive_baselines import predictive_baselines


class PredictiveBaselineTests(unittest.TestCase):
    def test_baseline_identifies_feature(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            feature_path = tmp_path / "features.parquet"
            label_path = tmp_path / "labels.parquet"
            features = pd.DataFrame({"feature_1": [0, 1, 2, 3], "feature_2": [1, 1, 1, 1]})
            labels = pd.DataFrame({"future_return_24_bars": [0.0, 0.1, -0.2, 0.3]})
            pq.write_table(pa.Table.from_pandas(features), feature_path)
            pq.write_table(pa.Table.from_pandas(labels), label_path)
            report = predictive_baselines(feature_path, label_path)
            self.assertIn("best_feature", report)
            self.assertIn("threshold_search", report)


if __name__ == "__main__":
    unittest.main()

