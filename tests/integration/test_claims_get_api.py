"""HTTP tests for retrieving insurance claims."""

from unittest.mock import Mock

from fastapi.testclient import TestClient

from life_claims.api.main import app, get_claims_repository


def test_get_existing_claim_returns_200():
    repository = Mock()
    repository.get_by_request_id.return_value = {
        "id_solicitud": "SOL-00231",
        "numero_poliza": "AV-VI-0100791",
        "estado": "REGISTERED",
        "numero_siniestro": "SIN-001",
        "motivos_rechazo": [],
    }

    app.dependency_overrides[get_claims_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            response = client.get("/reclamaciones/SOL-00231")

        assert response.status_code == 200
        assert response.json() == repository.get_by_request_id.return_value
        repository.get_by_request_id.assert_called_once_with("SOL-00231")

    finally:
        app.dependency_overrides.clear()


def test_get_unknown_claim_returns_404():
    repository = Mock()
    repository.get_by_request_id.return_value = None

    app.dependency_overrides[get_claims_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            response = client.get("/reclamaciones/NO-EXISTE")

        assert response.status_code == 404
        repository.get_by_request_id.assert_called_once_with("NO-EXISTE")

    finally:
        app.dependency_overrides.clear()
