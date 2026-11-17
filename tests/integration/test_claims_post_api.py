"""HTTP tests for submitting insurance claims."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from life_claims.api.main import app, get_claims_service


def valid_claim():
    return {
        "id_solicitud": "SOL-00231",
        "canal": "CORREDOR",
        "numero_poliza": "AV-VI-0100791",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "2310351885",
        },
        "tipo_reclamacion": "ITP",
        "fecha_siniestro": "2014-11-08",
        "fecha_radicacion": "2014-11-23T11:02:17",
        "reclamante": {},
        "descripcion": "Reclamacion de prueba",
        "documentos_adjuntos": [],
    }


def test_post_claim_registers_valid_request():
    service = Mock()
    service.submit_claim.return_value = {
        "id_solicitud": "SOL-00231",
        "estado": "REGISTERED",
        "numero_siniestro": "SIN-001",
        "motivos_rechazo": [],
    }

    app.dependency_overrides[get_claims_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reclamaciones",
                json=valid_claim(),
            )

        assert response.status_code == 201
        assert response.json() == service.submit_claim.return_value
        service.submit_claim.assert_called_once_with(valid_claim())

    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("estado", "expected_status"),
    [
        ("REJECTED", 200),
        ("PENDING_CONFIRMATION", 202),
        ("IN_PROGRESS", 202),
    ],
)
def test_post_claim_maps_business_states(estado, expected_status):
    service = Mock()
    service.submit_claim.return_value = {
        "id_solicitud": "SOL-00231",
        "estado": estado,
        "numero_siniestro": None,
        "motivos_rechazo": ["R1"] if estado == "REJECTED" else [],
    }

    app.dependency_overrides[get_claims_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/reclamaciones", json=valid_claim())

        assert response.status_code == expected_status
        assert response.json()["estado"] == estado

    finally:
        app.dependency_overrides.clear()


def test_post_claim_returns_409_for_idempotency_conflict():
    service = Mock()
    service.submit_claim.side_effect = ValueError(
        "Idempotency conflict: request ID has different content"
    )

    app.dependency_overrides[get_claims_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/reclamaciones", json=valid_claim())

        assert response.status_code == 409
        assert "Idempotency conflict" in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()


def test_post_claim_returns_422_for_invalid_request():
    service = Mock()
    app.dependency_overrides[get_claims_service] = lambda: service

    try:
        payload = valid_claim()
        payload.pop("numero_poliza")

        with TestClient(app) as client:
            response = client.post("/reclamaciones", json=payload)

        assert response.status_code == 422
        service.submit_claim.assert_not_called()

    finally:
        app.dependency_overrides.clear()
