"""Rebuild the local knowledge index without downloading external sources."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utilities.ingest_dev_docs import prepare_directories, populate_sqlite_database


if __name__ == "__main__":
    prepare_directories()
    populate_sqlite_database()
