import unittest
from research.v89_data_catalog import expected_archive_names
from datetime import date

class DownloadPlanTests(unittest.TestCase):
    def test_partial_month_uses_daily_names(self):
        names=expected_archive_names(date(2020,5,22),date(2020,5,23))
        self.assertEqual(names,["BTCUSDT-aggTrades-2020-05-22.zip","BTCUSDT-aggTrades-2020-05-23.zip"])
