"""TestDataLoader module for CSIT314 Large-Scale Test Data Generation."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.generate_large_scale_data import generate_large_scale_data


def load_test_data(db_path: str = "data/large_scale.sqlite") -> dict:
    """Safely loads approximately 100+ records per entity into the target database."""
    return generate_large_scale_data(db_path)


if __name__ == "__main__":
    load_test_data()

