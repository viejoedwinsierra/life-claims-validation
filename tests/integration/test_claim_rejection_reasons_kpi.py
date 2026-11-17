"""Integration tests for rejection-reason SQL analytics."""

import json
import sqlite3
from pathlib import Path

from life_claims.infrastructure.init_claims_db import initialize_database

SQL_PATH = Path("datos/queries/007_claim_rejection_reasons.sql")
MIGRATION_PATH = Path("datos/migrations/001_create_claims.sql")


def run_kpi(tmp_path, scenarios):
    database = tmp_path / "claims.sqlite3"
    initialize_database(database, MIGRATION_PATH)

    with sqlite3.connect(database) as db:
        for request_id, state, reasons in scenarios:
            db.execute(
                """
                INSERT INTO reclamaciones (
                    id_solicitud, payload_hash, numero_poliza,
                    payload_json, estado, motivos_rechazo_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    f"hash-{request_id}",
                    "POL-TEST",
                    json.dumps({"id_solicitud": request_id}),
                    state,
                    json.dumps(reasons),
                ),
            )

        cursor = db.execute(SQL_PATH.read_text(encoding="utf-8"))
        columns = [column[0] for column in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


def test_rejection_reasons_and_excluded_states(tmp_path):
    scenarios = [
        ("A", "REJECTED", ["R1", "R3"]),
        ("B", "REJECTED", ["R3"]),
        ("C", "REJECTED", ["R8"]),
        ("D", "REGISTERED", []),
        ("E", "TECHNICAL_ERROR", []),
        ("F", "RECEIVED", []),
    ]

    rows = run_kpi(tmp_path, scenarios)
    result = {row["motivo"]: row for row in rows}

    assert set(result) == {"R1", "R3", "R8"}

    for row in rows:
        assert row["evaluated_claims"] == 4
        assert row["rejected_claims"] == 3
        assert row["porcentaje_rechazo_global"] == 75.0

    assert result["R1"]["porcentaje_evaluadas_por_motivo"] == 25.0
    assert result["R3"]["porcentaje_evaluadas_por_motivo"] == 50.0
    assert result["R8"]["porcentaje_evaluadas_por_motivo"] == 25.0

    assert result["R1"]["porcentaje_distribucion_motivos"] == 25.0
    assert result["R3"]["porcentaje_distribucion_motivos"] == 50.0
    assert result["R8"]["porcentaje_distribucion_motivos"] == 25.0


def test_repeated_reason_counts_distinct_requests(tmp_path):
    scenarios = [
        ("A", "REJECTED", ["R1", "R1", "R3"]),
        ("B", "REGISTERED", []),
    ]

    rows = run_kpi(tmp_path, scenarios)
    result = {row["motivo"]: row for row in rows}

    assert result["R1"]["solicitudes_con_motivo"] == 1
    assert result["R1"]["ocurrencias"] == 2
    assert result["R1"]["porcentaje_evaluadas_por_motivo"] == 50.0
    assert result["R1"]["porcentaje_distribucion_motivos"] == 66.67

    assert result["R3"]["solicitudes_con_motivo"] == 1
    assert result["R3"]["ocurrencias"] == 1
    assert result["R3"]["porcentaje_distribucion_motivos"] == 33.33


def test_no_rejections_returns_no_reason_rows(tmp_path):
    rows = run_kpi(
        tmp_path,
        [
            ("A", "REGISTERED", []),
            ("B", "TECHNICAL_ERROR", []),
        ],
    )

    assert rows == []
