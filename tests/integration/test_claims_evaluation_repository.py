"""Persistence tests for read-only claim evaluations."""

import sqlite3
from pathlib import Path

import pytest

from life_claims.infrastructure.claims_evaluation_repository import (
    ClaimsEvaluationRepository,
)

MIGRATIONS = Path("datos/migrations")


def test_save_evaluation_run_preserves_business_and_technical_results(
    tmp_path,
):
    database = tmp_path / "evaluations.sqlite3"

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
            VALUES ('claims.json', 'evaluation-test-hash', 2)
            """
        ).lastrowid

        connection.executemany(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number,
                id_solicitud, payload_json
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (batch_id, 1, "REQ-001", '{"id_solicitud":"REQ-001"}'),
                (batch_id, 2, "REQ-002", '{"id_solicitud":"REQ-002"}'),
            ],
        )

    repository = ClaimsEvaluationRepository(database)

    run_id = repository.save_run(
        batch_id=batch_id,
        evaluation_date="2026-11-17",
        r8_source="REGISTERED_ONLY",
        results=[
            {
                "id_solicitud": "REQ-001",
                "estado": "REJECTED",
                "motivos_rechazo": ["R1", "R3"],
            },
            {
                "id_solicitud": "REQ-002",
                "estado": "TECHNICAL_ERROR",
                "motivos_rechazo": [],
                "error_tecnico": "TIMEOUT",
            },
        ],
    )

    with sqlite3.connect(database) as connection:
        run = connection.execute(
            """
            SELECT batch_id, evaluation_date,
                   evaluation_method, r8_source
            FROM claims_evaluation_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        saved = connection.execute(
            """
            SELECT a.id_solicitud, r.estado,
                   r.motivos_rechazo_json, r.error_tecnico
            FROM claims_evaluation_results AS r
            JOIN reclamaciones_analytics AS a
              ON a.raw_id = r.raw_id
             AND a.batch_id = r.batch_id
            WHERE r.run_id = ?
            ORDER BY a.source_row_number
            """,
            (run_id,),
        ).fetchall()

    assert run == (
        batch_id,
        "2026-11-17",
        "READ_ONLY",
        "REGISTERED_ONLY",
    )

    assert saved == [
        ("REQ-001", "REJECTED", '["R1", "R3"]', None),
        ("REQ-002", "TECHNICAL_ERROR", "[]", "TIMEOUT"),
    ]


def test_save_run_is_atomic_for_incomplete_duplicate_and_invalid_results(
    tmp_path,
):
    """Invalid batches must not leave partial evaluation records."""
    database = tmp_path / "atomic_evaluations.sqlite3"

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
            VALUES ('atomic.json', 'atomic-test-hash', 2)
            """
        ).lastrowid

        connection.executemany(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number,
                id_solicitud, payload_json
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (batch_id, 1, "REQ-A", '{"id_solicitud":"REQ-A"}'),
                (batch_id, 2, "REQ-B", '{"id_solicitud":"REQ-B"}'),
            ],
        )

    repository = ClaimsEvaluationRepository(database)

    valid = {
        "id_solicitud": "REQ-A",
        "estado": "VALID",
        "motivos_rechazo": [],
    }

    rejected = {
        "id_solicitud": "REQ-B",
        "estado": "REJECTED",
        "motivos_rechazo": ["R1"],
    }

    scenarios = [
        (
            [valid],
            ValueError,
        ),
        (
            [valid, valid],
            ValueError,
        ),
        (
            [
                valid,
                {
                    **rejected,
                    "motivos_rechazo": ["R99"],
                },
            ],
            sqlite3.IntegrityError,
        ),
    ]

    for results, expected_error in scenarios:
        with pytest.raises(expected_error):
            repository.save_run(
                batch_id=batch_id,
                evaluation_date="2026-11-17",
                r8_source="REGISTERED_ONLY",
                results=results,
            )

        with sqlite3.connect(database) as connection:
            runs = connection.execute(
                "SELECT COUNT(*) FROM claims_evaluation_runs"
            ).fetchone()[0]

            saved_results = connection.execute(
                "SELECT COUNT(*) FROM claims_evaluation_results"
            ).fetchone()[0]

            original_claims = connection.execute(
                "SELECT COUNT(*) FROM reclamaciones_analytics"
            ).fetchone()[0]

        assert runs == 0
        assert saved_results == 0
        assert original_claims == 2


def test_save_run_preserves_independent_evaluation_history(tmp_path):
    """Repeated evaluations must preserve independent historical results."""
    database = tmp_path / "evaluation_history.sqlite3"

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
            VALUES ('history.json', 'history-test-hash', 1)
            """
        ).lastrowid

        connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number,
                id_solicitud, payload_json
            )
            VALUES (?, 1, 'REQ-HISTORY', '{}')
            """,
            (batch_id,),
        )

    repository = ClaimsEvaluationRepository(database)

    first_run = repository.save_run(
        batch_id=batch_id,
        evaluation_date="2026-11-17",
        r8_source="REGISTERED_ONLY",
        results=[
            {
                "id_solicitud": "REQ-HISTORY",
                "estado": "VALID",
                "motivos_rechazo": [],
            }
        ],
    )

    second_run = repository.save_run(
        batch_id=batch_id,
        evaluation_date="2026-11-18",
        r8_source="REGISTERED_ONLY",
        results=[
            {
                "id_solicitud": "REQ-HISTORY",
                "estado": "REJECTED",
                "motivos_rechazo": ["R1"],
            }
        ],
    )

    with sqlite3.connect(database) as connection:
        history = connection.execute(
            """
            SELECT r.run_id, e.evaluation_date,
                   r.estado, r.motivos_rechazo_json
            FROM claims_evaluation_results AS r
            JOIN claims_evaluation_runs AS e
              ON e.run_id = r.run_id
             AND e.batch_id = r.batch_id
            ORDER BY r.run_id
            """
        ).fetchall()

    assert first_run != second_run
    assert history == [
        (first_run, "2026-11-17", "VALID", "[]"),
        (second_run, "2026-11-18", "REJECTED", '["R1"]'),
    ]


def test_save_run_requires_core_snapshot_fingerprint(tmp_path):
    """Each run must identify the Core data snapshot used."""
    database = tmp_path / "snapshot_evaluation.sqlite3"

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
            VALUES ('snapshot.json', 'snapshot-test-hash', 1)
            """
        ).lastrowid

        connection.execute(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id, source_row_number,
                id_solicitud, payload_json
            )
            VALUES (?, 1, 'REQ-SNAPSHOT', '{}')
            """,
            (batch_id,),
        )

    fingerprint = "a" * 64
    repository = ClaimsEvaluationRepository(database)

    run_id = repository.save_run(
        batch_id=batch_id,
        evaluation_date="2026-11-17",
        r8_source="REGISTERED_ONLY",
        core_snapshot_sha256=fingerprint,
        results=[
            {
                "id_solicitud": "REQ-SNAPSHOT",
                "estado": "VALID",
                "motivos_rechazo": [],
            }
        ],
    )

    with sqlite3.connect(database) as connection:
        saved = connection.execute(
            """
            SELECT core_snapshot_sha256
            FROM claims_evaluation_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert saved == (fingerprint,)
