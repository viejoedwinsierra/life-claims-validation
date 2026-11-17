"""End-to-end read-only evaluation and persistence."""

import json
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import httpx

from life_claims.application.claims_evaluation_workflow import (
    evaluate_and_save_batch,
)

MIGRATIONS = Path("datos/migrations")


def test_evaluate_and_save_batch_preserves_all_outcomes(tmp_path):
    database = tmp_path / "workflow.sqlite3"

    claims = [
        {
            "id_solicitud": "REQ-VALID",
            "numero_poliza": "POL-001",
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "123",
            },
            "fecha_siniestro": "2026-11-01",
            "fecha_radicacion": "2026-11-10",
            "tipo_reclamacion": "MUERTE",
            "canal": "WEB",
        },
        {
            "id_solicitud": "REQ-REJECTED",
            "numero_poliza": "POL-MISSING",
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "456",
            },
            "fecha_siniestro": "2026-11-01",
            "fecha_radicacion": "2026-11-10",
            "tipo_reclamacion": "MUERTE",
            "canal": "WEB",
        },
        {
            "id_solicitud": "REQ-TIMEOUT",
            "numero_poliza": "POL-TIMEOUT",
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "789",
            },
            "fecha_siniestro": "2026-11-01",
            "fecha_radicacion": "2026-11-10",
            "tipo_reclamacion": "MUERTE",
            "canal": "WEB",
        },
    ]

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
            VALUES ('workflow.json', 'workflow-hash', 3)
            """
        ).lastrowid

        for position, claim in enumerate(claims, start=1):
            connection.execute(
                """
                INSERT INTO reclamaciones_analytics (
                    batch_id, source_row_number,
                    id_solicitud, numero_poliza, payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    position,
                    claim["id_solicitud"],
                    claim["numero_poliza"],
                    json.dumps(claim),
                ),
            )

    core = Mock()

    def get_policy(number):
        if number == "POL-TIMEOUT":
            raise httpx.ReadTimeout("Simulated Core timeout")
        if number == "POL-MISSING":
            return None
        return {
            "numero_poliza": number,
            "estado": "VIGENTE",
            "tipo_documento_asegurado": "CC",
            "numero_documento_asegurado": "123",
            "fecha_inicio_vigencia": "2026-01-01",
            "fecha_fin_vigencia": "2026-12-31",
            "fecha_cambio_estado": None,
            "amparos": ["MUERTE"],
        }

    core.get_policy.side_effect = get_policy

    run_id = evaluate_and_save_batch(
        database=database,
        batch_id=batch_id,
        core=core,
        today=date(2026, 11, 17),
        r8_source="REGISTERED_ONLY",
    )

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT a.id_solicitud, e.estado,
                   e.motivos_rechazo_json, e.error_tecnico
            FROM claims_evaluation_results e
            JOIN reclamaciones_analytics a ON a.raw_id = e.raw_id
            WHERE e.run_id = ?
            ORDER BY a.source_row_number
            """,
            (run_id,),
        ).fetchall()

    assert len(rows) == 3
    assert rows[0][1] == "VALID"
    assert rows[1][1] == "REJECTED"
    assert rows[2][1:] == ("TECHNICAL_ERROR", "[]", "TIMEOUT")

    core.create_claim.assert_not_called()
