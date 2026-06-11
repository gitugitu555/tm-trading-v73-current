import unittest

from research.v86_recovery import args_hash, canonical_cli_args


class ManifestHashTests(unittest.TestCase):
    def test_hash_detects_identical_resolved_args(self):
        first = ["--target-pct", "0.005", "--entry-lag-bars", "1"]
        second = ["--entry-lag-bars", "1", "--target-pct", "0.005"]
        self.assertEqual(canonical_cli_args(first), canonical_cli_args(second))
        self.assertEqual(args_hash(first), args_hash(second))

    def test_last_repeated_option_wins(self):
        self.assertEqual(
            canonical_cli_args(["--entry-lag-bars", "1", "--entry-lag-bars", "0"]),
            ["--entry-lag-bars", "0"],
        )
