"""Verify migration 006 against an existing evaluation schema."""

import sqlite3
from pathlib import Path

import pytest

MIGRATIONS = Path("datos/migrations")


def test_snapshot_upgrade_preserves_existing_evaluations(tmp_path):
    database = tmp_path / "before_snapshot_upgrade.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Simulate migration 004 before the snapshot column existed.
        original_schema = (
            MIGRATIONS / "004_create_claims_evaluations.sql"
        ).read_text(encoding="utf-8")

        original_schema = original_schema.replace(
            """    core_snapshot_sha256 TEXT
        CHECK (
            core_snapshot_sha256 IS NULL
            OR (
                length(core_snapshot_sha256) = 64
                AND core_snapshot_sha256 NOT GLOB '*[^0-9a-f]*'
            )
        ),
""",
            "",
        )

        connection.executescript(
            (
                MIGRATIONS / "003_create_claims_analytics.sql"
            ).read_text(encoding="utf-8")
        )
        connection.executescript(original_schema)

        batch_id = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('existing.json', 'existing-batch-hash', 1)
            """
        ).lastrowid

        raw_id = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number,
                id_solicitud, payload_json
            )
            VALUES (?, 1, 'REQ-OLD', '{}')
            """,
            (batch_id,),
        ).lastrowid

        run_id = connection.execute(
            """
            INSERT INTO claims_evaluation_runs (
                batch_id, evaluation_date,
                evaluation_method, r8_source
            )
            VALUES (?, '2026-11-17', 'READ_ONLY', 'NONE')
            """,
            (batch_id,),
        ).lastrowid

        connection.execute(
            """
            INSERT INTO claims_evaluation_results (
                run_id, batch_id, raw_id,
                estado, motivos_rechazo_json
            )
            VALUES (?, ?, ?, 'VALID', '[]')
            """,
            (run_id, batch_id, raw_id),
        )

        migration = (
            MIGRATIONS / "006_add_core_snapshot_fingerprint.sql"
        ).read_text(encoding="utf-8")

        connection.executescript(migration)

        existing = connection.execute(
            """
            SELECT core_snapshot_sha256
            FROM claims_evaluation_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        assert existing == (None,)

        fingerprint = "a" * 64

        connection.execute(
            """
            UPDATE claims_evaluation_runs
            SET core_snapshot_sha256 = ?
            WHERE run_id = ?
            """,
            (fingerprint, run_id),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE claims_evaluation_runs
                SET core_snapshot_sha256 = 'INVALID'
                WHERE run_id = ?
                """,
                (run_id,),
            )

        saved = connection.execute(
            """
            SELECT core_snapshot_sha256
            FROM claims_evaluation_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        results = connection.execute(
            """
            SELECT estado, motivos_rechazo_json
            FROM claims_evaluation_results
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchall()

        assert saved == (fingerprint,)
        assert results == [("VALID", "[]")]
        assert connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] == "ok"
        assert connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall() == []
