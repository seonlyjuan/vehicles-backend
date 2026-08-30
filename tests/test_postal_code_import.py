import tempfile
import unittest
from pathlib import Path

from scripts.import_swiss_postal_codes import read_records


class PostalCodeImportTests(unittest.TestCase):
    def test_reads_official_style_german_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "postal_codes.csv"
            path.write_text("PLZ;Ortschaftsname;Kantonskürzel\n8004;Zürich;ZH\n", encoding="utf-8")
            self.assertEqual(read_records(path), [{
                "postal_code": "8004",
                "locality": "Zürich",
                "canton": "ZH",
            }])


if __name__ == "__main__":
    unittest.main()
