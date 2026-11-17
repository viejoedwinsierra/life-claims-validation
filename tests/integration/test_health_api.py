"""Integration tests for the HTTP health endpoint."""

from fastapi.testclient import TestClient

from life_claims.api.main import app


def test_health_returns_http_200():
    """The application exposes a basic liveness endpoint."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
