import unittest
from datetime import date
from research.v89_data_catalog import coverage_audit

class CoverageTests(unittest.TestCase):
    def test_missing_archive_fails(self):
        audit=coverage_audit([],start=date(2020,5,22),end=date(2020,5,22))
        self.assertFalse(audit["coverage_passed"])
        self.assertTrue(audit["missing_archives"])
