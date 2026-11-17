"""Tests for repeatable SQLite initialization."""

import sqlite3
from pathlib import Path

from life_claims.infrastructure.init_claims_db import initialize_database

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "datos/migrations/001_create_claims.sql"


def test_initialization_preserves_existing_claims(tmp_path):
    database = tmp_path / "claims.db"

    initialize_database(database, MIGRATION)

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO reclamaciones (
                id_solicitud, payload_hash, business_event_key,
                numero_poliza, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("SOL-P008-001", "hash", None, "AV-TEST", "{}"),
        )

    initialize_database(database, MIGRATION)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT id_solicitud FROM reclamaciones"
        ).fetchall()

    assert rows == [("SOL-P008-001",)]
