"""Integration tests for claim counts by type and channel."""

import json
import sqlite3
from pathlib import Path

from life_claims.infrastructure.claims_json_ingestion import ingest_claims_json


def test_claims_by_type_channel_kpi(tmp_path):
    source = tmp_path / "claims.json"
    database = tmp_path / "analytics.sqlite3"

    combinations = [
        ("MUERTE", "WEB"),
        ("MUERTE", "WEB"),
        ("MUERTE", "APP"),
        ("ITP", "WEB"),
    ]

    claims = [
        {
            "id_solicitud": f"REQ-{index}",
            "numero_poliza": "POL-001",
            "tipo_reclamacion": claim_type,
            "canal": channel,
            "fecha_siniestro": "2024-01-01",
            "fecha_radicacion": "2024-01-10T10:00:00",
        }
        for index, (claim_type, channel) in enumerate(
            combinations, start=1
        )
    ]

    source.write_text(json.dumps(claims), encoding="utf-8")
    ingest_claims_json(source, database)

    sql = Path(
        "datos/queries/006_claims_by_type_channel.sql"
    ).read_text(encoding="utf-8")

    with sqlite3.connect(database) as connection:
        rows = connection.execute(sql).fetchall()

    result = {
        (row[0], row[1]): (row[2], row[3], row[4])
        for row in rows
    }

    assert len(result) == 3
    assert result[("MUERTE", "WEB")] == (2, 4, 50.0)
    assert result[("MUERTE", "APP")] == (1, 4, 25.0)
    assert result[("ITP", "WEB")] == (1, 4, 25.0)

    assert sum(row[0] for row in result.values()) == 4
    assert sum(row[2] for row in result.values()) == 100.0
