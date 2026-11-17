"""Initialize the SQLite claims database from versioned SQL."""

import os
import sqlite3
from pathlib import Path


def initialize_database(
    database_path: str | Path,
    migration_path: str | Path,
) -> None:
    """Create the claims schema without deleting existing records."""
    database_path = Path(database_path)
    migration_path = Path(migration_path)

    database_path.parent.mkdir(parents=True, exist_ok=True)

    sql = migration_path.read_text(encoding="utf-8")

    with sqlite3.connect(database_path, timeout=10) as connection:
        connection.executescript(sql)


def main() -> None:
    """Initialize the database configured for the API."""
    database_path = os.environ["CLAIMS_DB_PATH"]
    migration_path = Path("/app/datos/migrations/001_create_claims.sql")

    initialize_database(database_path, migration_path)


if __name__ == "__main__":
    main()
