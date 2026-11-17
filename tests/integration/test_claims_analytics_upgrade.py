"""Integration tests for upgrading an existing analytics database."""

import sqlite3
from pathlib import Path

MIGRATIONS = Path("datos/migrations")


def test_legacy_analytics_upgrade_preserves_claims(tmp_path):
    database = tmp_path / "legacy_analytics.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Simulate the schema before the composite uniqueness change.
        connection.executescript(
            """
            CREATE TABLE claims_ingestion_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_filename TEXT NOT NULL,
                source_sha256 TEXT NOT NULL UNIQUE,
                rows_inserted INTEGER NOT NULL
            );

            CREATE TABLE reclamaciones_analytics (
                raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                source_row_number INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY (batch_id)
                    REFERENCES claims_ingestion_batches(batch_id),
                UNIQUE (batch_id, source_row_number)
            );
            """
        )

        connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('legacy.json', 'legacy-hash', 2)
            """
        )

        connection.executemany(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number, payload_json
            )
            VALUES (1, ?, ?)
            """,
            [
                (1, '{"id_solicitud":"A"}'),
                (2, '{"id_solicitud":"B"}'),
            ],
        )

        before = connection.execute(
            """
            SELECT raw_id, batch_id, source_row_number, payload_json
            FROM reclamaciones_analytics
            ORDER BY raw_id
            """
        ).fetchall()

        upgrade = (
            MIGRATIONS / "005_upgrade_claims_analytics.sql"
        ).read_text(encoding="utf-8")

        evaluations = (
            MIGRATIONS / "004_create_claims_evaluations.sql"
        ).read_text(encoding="utf-8")

        connection.executescript(upgrade)
        connection.executescript(upgrade)
        connection.executescript(evaluations)

        after = connection.execute(
            """
            SELECT raw_id, batch_id, source_row_number, payload_json
            FROM reclamaciones_analytics
            ORDER BY raw_id
            """
        ).fetchall()

        assert after == before
        assert len(after) == 2

        assert connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] == "ok"

        assert connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall() == []

        connection.execute(
            """
            INSERT INTO claims_evaluation_runs (
                batch_id, evaluation_date,
                evaluation_method, r8_source
            )
            VALUES (1, '2026-11-17', 'READ_ONLY', 'NONE')
            """
        )

        connection.execute(
            """
            INSERT INTO claims_evaluation_results (
                run_id, batch_id, raw_id,
                estado, motivos_rechazo_json
            )
            VALUES (1, 1, 1, 'REJECTED', '["R1"]')
            """
        )

        assert connection.execute(
            "SELECT COUNT(*) FROM claims_evaluation_results"
        ).fetchone()[0] == 1
