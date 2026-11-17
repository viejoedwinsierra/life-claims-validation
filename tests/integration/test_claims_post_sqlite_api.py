"""End-to-end HTTP tests with SQLite and a simulated core."""

import sqlite3
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from life_claims.api.main import app

MIGRATION = Path(__file__).resolve().parents[2] / "datos" / "migrations" / "001_create_claims.sql"


def test_post_missing_policy_is_rejected_and_persisted(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "claims.sqlite3"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    requests_received = []

    def core_handler(request):
        requests_received.append(request)

        if request.method == "GET" and request.url.path.startswith("/api/v1/polizas/"):
            return httpx.Response(404)

        raise AssertionError(f"Unexpected core request: {request.method} {request.url.path}")

    def http_client_factory():
        return httpx.Client(
            transport=httpx.MockTransport(core_handler),
            base_url="http://core.test",
        )

    monkeypatch.setattr(
        "life_claims.api.main.create_core_http_client",
        http_client_factory,
    )

    claim = {
        "id_solicitud": "SOL-API-007D-001",
        "canal": "WEB",
        "numero_poliza": "AV-VI-NO-EXISTE",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15T10:30:00",
    }

    with TestClient(app) as client:
        post_response = client.post("/reclamaciones", json=claim)

        assert post_response.status_code == 200
        assert post_response.json()["estado"] == "REJECTED"
        assert "R1" in post_response.json()["motivos_rechazo"]

        get_response = client.get("/reclamaciones/SOL-API-007D-001")

    assert get_response.status_code == 200
    assert get_response.json()["estado"] == "REJECTED"
    assert "R1" in get_response.json()["motivos_rechazo"]

    assert len(requests_received) == 1
    assert requests_received[0].method == "GET"


def test_post_valid_claim_registers_once_and_is_idempotent(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "claims.sqlite3"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    requests_received = []

    policy = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "2123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }

    def core_handler(request):
        requests_received.append(request)

        if request.method == "GET":
            assert request.url.path == "/api/v1/polizas/AV-VI-0100000"
            return httpx.Response(200, json=policy)

        if request.method == "POST":
            assert request.url.path == "/api/v1/siniestros"
            assert request.headers["Idempotency-Key"] == "SOL-API-007E-001"

            return httpx.Response(
                201,
                json={
                    "numero_siniestro": "SIN-API-007E-001",
                    "estado_core": "REGISTRADO",
                },
            )

        raise AssertionError("Unexpected core request")

    def http_client_factory():
        return httpx.Client(
            transport=httpx.MockTransport(core_handler),
            base_url="http://core.test",
        )

    monkeypatch.setattr(
        "life_claims.api.main.create_core_http_client",
        http_client_factory,
    )

    claim = {
        "id_solicitud": "SOL-API-007E-001",
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

    with TestClient(app) as client:
        first = client.post("/reclamaciones", json=claim)
        second = client.post("/reclamaciones", json=claim)
        stored = client.get("/reclamaciones/SOL-API-007E-001")

    assert first.status_code == 201
    assert first.json()["estado"] == "REGISTERED"
    assert first.json()["numero_siniestro"] == "SIN-API-007E-001"

    assert second.status_code == 201
    assert second.json() == first.json()

    assert stored.status_code == 200
    assert stored.json()["estado"] == "REGISTERED"
    assert stored.json()["numero_siniestro"] == "SIN-API-007E-001"

    assert len(requests_received) == 2
    assert [request.method for request in requests_received] == [
        "GET",
        "POST",
    ]


def test_post_core_timeout_is_pending_and_not_retried(
    monkeypatch,
    tmp_path,
):
    """A core timeout must preserve uncertainty and prevent duplicate POSTs."""
    database_path = tmp_path / "claims.sqlite3"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    requests_received = []

    policy = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "2123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }

    def core_handler(request):
        requests_received.append(request)

        if request.method == "GET":
            return httpx.Response(200, json=policy)

        if request.method == "POST":
            assert request.headers["Idempotency-Key"] == "SOL-API-007F-001"
            raise httpx.ReadTimeout(
                "Core response timed out",
                request=request,
            )

        raise AssertionError("Unexpected core request")

    def http_client_factory():
        return httpx.Client(
            transport=httpx.MockTransport(core_handler),
            base_url="http://core.test",
        )

    monkeypatch.setattr(
        "life_claims.api.main.create_core_http_client",
        http_client_factory,
    )

    claim = {
        "id_solicitud": "SOL-API-007F-001",
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

    with TestClient(app) as client:
        first = client.post("/reclamaciones", json=claim)
        second = client.post("/reclamaciones", json=claim)
        stored = client.get("/reclamaciones/SOL-API-007F-001")

    assert first.status_code == 202
    assert first.json()["estado"] == "PENDING_CONFIRMATION"
    assert first.json()["numero_siniestro"] is None

    assert second.status_code == 202
    assert second.json() == first.json()

    assert stored.status_code == 200
    assert stored.json()["estado"] == "PENDING_CONFIRMATION"

    assert [request.method for request in requests_received] == [
        "GET",
        "POST",
    ]
