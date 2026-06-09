import unittest
from research.cpcv import purge_and_embargo_splits

class CPCVTests(unittest.TestCase):
    def test_purge_and_embargo_logic(self) -> None:
        # 10 events, spaced by 10 units each
        # entry times: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90
        event_times = [i * 10 for i in range(10)]
        # exit times: entries plus 15 units (overlap duration)
        exit_times = [entry + 15 for entry in event_times]

        # Test set: entries between 40 and 60 (indices 4, 5, 6)
        # test_start = 40, test_end = 60
        # Embargo duration: 10 units of time (blocks entry times up to 60 + 10 = 70, so index 7 is blocked)
        train_indices = purge_and_embargo_splits(
            event_times=event_times,
            exit_times=exit_times,
            test_start=40,
            test_end=60,
            embargo_duration=10
        )

        # Expected indices:
        # idx 0: entry 0, exit 15 (safe)
        # idx 1: entry 10, exit 25 (safe)
        # idx 2: entry 20, exit 35 (safe)
        # idx 3: entry 30, exit 45 (purged because exit 45 >= test_start 40)
        # idx 4, 5, 6: in test set (removed)
        # idx 7: entry 70 (embargoed because test_end is 60, embargo_duration is 10, so event 70 <= 70 is blocked)
        # idx 8: entry 80 (safe)
        # idx 9: entry 90 (safe)
        self.assertIn(0, train_indices)
        self.assertIn(1, train_indices)
        self.assertIn(2, train_indices)
        self.assertNotIn(3, train_indices)  # Purged
        self.assertNotIn(4, train_indices)  # Test set
        self.assertNotIn(7, train_indices)  # Embargoed
        self.assertIn(8, train_indices)
        self.assertIn(9, train_indices)

if __name__ == "__main__":
    unittest.main()
