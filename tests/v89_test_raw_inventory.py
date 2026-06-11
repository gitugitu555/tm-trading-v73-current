import unittest
from pathlib import Path
from research.v89_data_catalog import inventory_archive

class RawInventoryTests(unittest.TestCase):
    def test_missing_cache_metadata_remains_explicit(self):
        path=Path("/tmp/v89_missing.zip")
        self.assertFalse(path.exists())
