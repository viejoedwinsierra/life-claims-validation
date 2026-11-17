"""Integration tests for analytical evaluation persistence."""

import sqlite3
from pathlib import Path

import pytest

MIGRATIONS = (
    Path(__file__).resolve().parents[2]
    / "datos/migrations"
)


def test_evaluation_schema_preserves_runs_and_results(tmp_path):
    """Each run must retain one result per original source row."""
    database = tmp_path / "evaluation.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript(
            (MIGRATIONS / "003_create_claims_analytics.sql")
            .read_text(encoding="utf-8")
        )

        connection.executescript(
            (MIGRATIONS / "004_create_claims_evaluations.sql")
            .read_text(encoding="utf-8")
        )

        cursor = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename,
                source_sha256,
                rows_inserted
            )
            VALUES (?, ?, ?)
            """,
            ("claims.json", "sha256-test", 1),
        )
        batch_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id,
                source_row_number,
                payload_json
            )
            VALUES (?, ?, ?)
            """,
            (batch_id, 1, '{"id_solicitud":"SOL-001"}'),
        )
        raw_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO claims_evaluation_runs (
                batch_id,
                evaluation_date,
                evaluation_method,
                r8_source
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                batch_id,
                "2026-11-17",
                "READ_ONLY",
                "REGISTERED_CLAIMS_REPOSITORY",
            ),
        )
        run_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO claims_evaluation_results (
                run_id,
                batch_id,
                    raw_id,
                estado,
                motivos_rechazo_json,
                error_tecnico
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, batch_id, raw_id, "REJECTED", '["R8"]', None),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO claims_evaluation_results (
                    run_id,
                    batch_id,
                    raw_id,
                    estado,
                    motivos_rechazo_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, batch_id, raw_id, "VALID", "[]"),
            )

        rows = connection.execute(
            """
            SELECT
                r.evaluation_method,
                r.r8_source,
                e.estado,
                e.motivos_rechazo_json
            FROM claims_evaluation_results AS e
            JOIN claims_evaluation_runs AS r
                ON r.run_id = e.run_id
            """
        ).fetchall()

    assert rows == [
        (
            "READ_ONLY",
            "REGISTERED_CLAIMS_REPOSITORY",
            "REJECTED",
            '["R8"]',
        )
    ]


def test_evaluation_rejects_claim_from_another_batch(tmp_path):
    """A result cannot reference a claim from a different batch."""
    database = tmp_path / "cross_batch.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for migration in (
            "003_create_claims_analytics.sql",
            "004_create_claims_evaluations.sql",
        ):
            connection.executescript(
                (MIGRATIONS / migration).read_text(encoding="utf-8")
            )

        batch_a = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('a.json', 'hash-a', 0)
            """
        ).lastrowid

        batch_b = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('b.json', 'hash-b', 1)
            """
        ).lastrowid

        raw_b = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number, payload_json
            )
            VALUES (?, 1, '{}')
            """,
            (batch_b,),
        ).lastrowid

        run_a = connection.execute(
            """
            INSERT INTO claims_evaluation_runs (
                batch_id, evaluation_date,
                evaluation_method, r8_source
            )
            VALUES (?, '2026-11-17', 'READ_ONLY', 'NONE')
            """,
            (batch_a,),
        ).lastrowid

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO claims_evaluation_results (
                    run_id, batch_id, raw_id,
                    estado, motivos_rechazo_json
                )
                VALUES (?, ?, ?, 'VALID', '[]')
                """,
                (run_a, batch_a, raw_b),
            )


def test_valid_result_cannot_have_rejection_reasons(tmp_path):
    """VALID results must not contain rejection reasons."""
    database = tmp_path / "invalid_result.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for migration in (
            "003_create_claims_analytics.sql",
            "004_create_claims_evaluations.sql",
        ):
            connection.executescript(
                (MIGRATIONS / migration).read_text(encoding="utf-8")
            )

        batch_id = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('test.json', 'hash-valid-check', 1)
            """
        ).lastrowid

        raw_id = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number, payload_json
            )
            VALUES (?, 1, '{}')
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

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO claims_evaluation_results (
                    run_id, batch_id, raw_id,
                    estado, motivos_rechazo_json
                )
                VALUES (?, ?, ?, 'VALID', '["R8"]')
                """,
                (run_id, batch_id, raw_id),
            )


def test_rejection_reasons_must_use_known_rule_codes(tmp_path):
    """Only business rule codes R1 through R8 are accepted."""
    database = tmp_path / "invalid_reason.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for migration in (
            "003_create_claims_analytics.sql",
            "004_create_claims_evaluations.sql",
        ):
            connection.executescript(
                (MIGRATIONS / migration).read_text(encoding="utf-8")
            )

        batch_id = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('test.json', 'hash-reason-check', 1)
            """
        ).lastrowid

        raw_id = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number, payload_json
            )
            VALUES (?, 1, '{}')
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

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO claims_evaluation_results (
                    run_id, batch_id, raw_id,
                    estado, motivos_rechazo_json
                )
                VALUES (?, ?, ?, 'REJECTED', '["R99"]')
                """,
                (run_id, batch_id, raw_id),
            )


def test_rejection_reason_triggers_validate_all_elements_and_updates(
    tmp_path,
):
    """Reject invalid reasons on INSERT and UPDATE."""
    database = tmp_path / "reason_triggers.sqlite3"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        for migration in (
            "003_create_claims_analytics.sql",
            "004_create_claims_evaluations.sql",
        ):
            connection.executescript(
                (MIGRATIONS / migration).read_text(encoding="utf-8")
            )

        batch_id = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename, source_sha256, rows_inserted
            )
            VALUES ('reasons.json', 'hash-reasons-multiple', 1)
            """
        ).lastrowid

        raw_id = connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number, payload_json
            )
            VALUES (?, 1, '{}')
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

        insert_sql = """
            INSERT INTO claims_evaluation_results (
                run_id, batch_id, raw_id,
                estado, motivos_rechazo_json
            )
            VALUES (?, ?, ?, 'REJECTED', ?)
        """

        for invalid in ('["R1", "R99"]', '["R1", null]'):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    insert_sql,
                    (run_id, batch_id, raw_id, invalid),
                )

        connection.execute(
            insert_sql,
            (run_id, batch_id, raw_id, '["R1", "R8"]'),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE claims_evaluation_results
                SET motivos_rechazo_json = '["R99"]'
                WHERE run_id = ?
                """,
                (run_id,),
            )

        saved = connection.execute(
            """
            SELECT motivos_rechazo_json
            FROM claims_evaluation_results
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()[0]

    assert saved == '["R1", "R8"]'
