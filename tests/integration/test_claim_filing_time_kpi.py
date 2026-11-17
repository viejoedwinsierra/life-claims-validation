"""Integration tests for the claim filing time SQL KPI."""

import json
import sqlite3
from pathlib import Path

from life_claims.infrastructure.claims_json_ingestion import (
    ingest_claims_json,
)


def test_claim_filing_time_kpi(tmp_path):
    source = tmp_path / "claims.json"
    database = tmp_path / "analytics.sqlite3"

    claims = [
        {
            "id_solicitud": f"REQ-{index}",
            "numero_poliza": "POL-001",
            "canal": "WEB",
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2024-01-01",
            "fecha_radicacion": filing_date,
        }
        for index, filing_date in enumerate(
            [
                "2024-01-01T10:00:00",
                "2025-12-31T10:00:00",
                "2026-01-01T10:00:00",
                "2023-12-31T10:00:00",
            ],
            start=1,
        )
    ]

    source.write_text(json.dumps(claims), encoding="utf-8")
    ingest_claims_json(source, database)

    sql = Path("datos/queries/005_claim_filing_time.sql").read_text(
        encoding="utf-8"
    )

    with sqlite3.connect(database) as connection:
        cursor = connection.execute(sql)
        result = dict(zip(
            [column[0] for column in cursor.description],
            cursor.fetchone(),
        ))

    assert result["total_reclamaciones"] == 4
    assert result["fechas_inconsistentes"] == 1
    assert result["dentro_plazo"] == 2
    assert result["radicaciones_tardias"] == 1
    assert result["reclamaciones_promedio"] == 3
    assert result["promedio_dias"] == 487.0
