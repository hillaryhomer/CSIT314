"""Unit test for TestDataLoader verifying 100+ records per entity."""
import tempfile
from pathlib import Path
import unittest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import connect_database
from tests.testdata.TestDataLoader import load_test_data


class TestDataLoaderTest(unittest.TestCase):
    def test_data_loader_generates_minimum_100_records_per_entity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "loader_test.sqlite")
            load_test_data(db_path)
            
            connection = connect_database(db_path)
            try:
                tables = [
                    "user_profiles", "user_accounts", "companies",
                    "project_categories", "interior_design_projects",
                    "favourites", "project_views", "report_events"
                ]
                for table in tables:
                    count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    self.assertGreaterEqual(count, 100, f"Table {table} count {count} is less than 100")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
