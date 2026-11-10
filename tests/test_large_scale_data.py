"""Automated test for large-scale test data generation (100+ records per entity)."""

import os
import tempfile
import unittest

from backend.database import connect_database
from backend.generate_large_scale_data import generate_large_scale_data


class LargeScaleDataGenerationTests(unittest.TestCase):
    def test_generates_at_least_100_records_per_entity_with_zero_foreign_key_violations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "test_large_scale.sqlite")
            generate_large_scale_data(db_path, min_count=100)

            connection = connect_database(db_path)
            try:
                # 1. Foreign key integrity
                fk_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
                self.assertEqual(len(fk_violations), 0, f"FK violations: {fk_violations}")

                # 2. Check 100+ records per entity
                tables = [
                    "user_profiles",
                    "user_accounts",
                    "companies",
                    "project_categories",
                    "interior_design_projects",
                    "favourites",
                    "project_views",
                    "report_events",
                ]
                for table in tables:
                    count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    self.assertGreaterEqual(
                        count, 100, f"Table {table} has {count} records, expected >= 100"
                    )

                # 3. Verify distinct search & filter functionality works under volume
                current_count = connection.execute(
                    "SELECT COUNT(*) FROM interior_design_projects WHERE status = 'Current'"
                ).fetchone()[0]
                past_count = connection.execute(
                    "SELECT COUNT(*) FROM interior_design_projects WHERE status = 'Past'"
                ).fetchone()[0]
                self.assertGreater(current_count, 40)
                self.assertGreater(past_count, 40)

                # 4. Verify search on indexed normalized column
                active_profiles = connection.execute(
                    "SELECT COUNT(*) FROM user_profiles WHERE status = 'Active'"
                ).fetchone()[0]
                self.assertGreater(active_profiles, 80)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()

