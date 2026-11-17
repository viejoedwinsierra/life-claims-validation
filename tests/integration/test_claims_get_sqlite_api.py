"""HTTP integration tests using a real SQLite claims database."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from life_claims.api.main import app
from life_claims.infrastructure.sqlite_claims_repository import (
    SQLiteClaimsRepository,
)

MIGRATION = Path(__file__).resolve().parents[2] / "datos" / "migrations" / "001_create_claims.sql"


def test_get_persisted_claim_returns_200(tmp_path, monkeypatch):
    database_path = tmp_path / "claims.sqlite3"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    repository = SQLiteClaimsRepository(database_path)

    claim = {
        "id_solicitud": "SOL-API-007B-001",
        "canal": "WEB",
        "numero_poliza": "AV-VI-0100000",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    assert repository.reserve_claim(claim) == "CREATED"

    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    with TestClient(app) as client:
        response = client.get("/reclamaciones/SOL-API-007B-001")

    assert response.status_code == 200

    body = response.json()

    assert body["id_solicitud"] == "SOL-API-007B-001"
    assert body["numero_poliza"] == "AV-VI-0100000"
    assert body["estado"] == "RECEIVED"
    assert body["numero_siniestro"] is None
    assert body["motivos_rechazo"] == []


def test_get_unknown_claim_from_sqlite_returns_404(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "claims.sqlite3"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    with TestClient(app) as client:
        response = client.get("/reclamaciones/NO-EXISTE")

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"
