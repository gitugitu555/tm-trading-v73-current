import unittest
from research.v89_data_catalog import canonical_hash

class HashStabilityTests(unittest.TestCase):
    def test_key_order_irrelevant(self):
        self.assertEqual(canonical_hash({"a":1,"b":2}),canonical_hash({"b":2,"a":1}))
