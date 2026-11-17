"""Integration tests for analytical claims ingestion."""

import json
import sqlite3

from life_claims.infrastructure.claims_json_ingestion import ingest_claims_json


def test_claims_ingestion_is_lossless_and_idempotent(tmp_path):
    source = tmp_path / "claims.json"
    database = tmp_path / "analytics.sqlite3"

    claim = {
        "id_solicitud": "REQ-001",
        "numero_poliza": "POL-001",
        "canal": "WEB",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-05T10:00:00",
    }

    source.write_text(
        json.dumps([claim, claim], ensure_ascii=False),
        encoding="utf-8",
    )

    first = ingest_claims_json(source, database)
    second = ingest_claims_json(source, database)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT id_solicitud, canal, tipo_reclamacion
            FROM reclamaciones_analytics
            ORDER BY source_row_number
            """
        ).fetchall()

        batches = connection.execute(
            "SELECT COUNT(*) FROM claims_ingestion_batches"
        ).fetchone()[0]

    assert first["rows_inserted"] == 2
    assert second["rows_inserted"] == 0
    assert batches == 1
    assert rows == [
        ("REQ-001", "WEB", "MUERTE"),
        ("REQ-001", "WEB", "MUERTE"),
    ]


def test_claims_ingestion_rejects_missing_file(tmp_path):
    """Missing source must raise FileNotFoundError."""
    import pytest

    source = tmp_path / "missing.json"
    database = tmp_path / "analytics.sqlite3"

    with pytest.raises(FileNotFoundError):
        ingest_claims_json(source, database)

    assert not database.exists()


def test_claims_ingestion_rejects_non_array_root(tmp_path):
    """The input document must contain a JSON array."""
    import pytest

    source = tmp_path / "claims.json"
    database = tmp_path / "analytics.sqlite3"
    source.write_text('{"id_solicitud": "REQ-001"}', encoding="utf-8")

    with pytest.raises(ValueError, match="root must be an array"):
        ingest_claims_json(source, database)

    assert not database.exists()


def test_claims_ingestion_rejects_non_object_records(tmp_path):
    """All array elements must be claim objects."""
    import pytest

    source = tmp_path / "claims.json"
    database = tmp_path / "analytics.sqlite3"
    source.write_text('[{"id_solicitud": "REQ-001"}, 123]', encoding="utf-8")

    with pytest.raises(ValueError, match="Every claim must be a JSON object"):
        ingest_claims_json(source, database)

    assert not database.exists()
