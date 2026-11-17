"""Execute policy coverage date quality queries."""

import sqlite3
from datetime import date
from pathlib import Path

QUERY_PATH = Path(__file__).resolve().parents[3] / "datos" / "queries" / "003_policy_validity.sql"


def is_valid_iso_date(value: str | None) -> int:
    """Return 1 for valid ISO calendar dates, otherwise 0."""
    if not isinstance(value, str):
        return 0

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return 0

    return int(value == parsed.isoformat())


def execute_policy_validity_kpi(
    database_path: str | Path,
    batch_id: int,
) -> list[dict]:
    """Aggregate coverage date quality for one ingestion batch."""
    query = QUERY_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        connection.create_function(
            "is_valid_iso_date",
            1,
            is_valid_iso_date,
            deterministic=True,
        )

        cursor = connection.execute(
            query,
            {"batch_id": batch_id},
        )

        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
