import csv
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from research.v90_duplicate_scan import scan_archives


class DuplicateScanCheckpointingTests(unittest.TestCase):
    def test_checkpoint_written_and_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "BTCUSDT-aggTrades-2020-01-01.zip"
            csv_path = tmp_path / "BTCUSDT-aggTrades-2020-01-01.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["1", "100", "1", "0", "0", "1590000000000", "True", ""])
                writer.writerow(["2", "101", "1", "0", "0", "1590000001000", "False", ""])
            with ZipFile(archive, "w") as zf:
                zf.write(csv_path, arcname=csv_path.name)
            checkpoint = tmp_path / "checkpoint.json"
            result = scan_archives([archive], checkpoint_path=checkpoint)
            self.assertTrue(result["scan_complete"])
            self.assertTrue(checkpoint.is_file())
            second = scan_archives([archive], checkpoint_path=checkpoint)
            self.assertTrue(second["scan_complete"])


if __name__ == "__main__":
    unittest.main()

