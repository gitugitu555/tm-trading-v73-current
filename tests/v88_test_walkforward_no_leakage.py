import unittest
from research.validation import walk_forward_splits

class WalkForwardLeakageTests(unittest.TestCase):
    def test_train_ends_before_test(self):
        for fold in walk_forward_splits(list(range(30)), train_size=10, test_size=5):
            self.assertLessEqual(fold.train_end, fold.test_start)
