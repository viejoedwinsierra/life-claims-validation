"""Tests for the application service HTTP dependency."""

from contextlib import contextmanager
from unittest.mock import Mock

import httpx

from life_claims.api.main import get_claims_service
from life_claims.application.claims_service import ClaimsApplicationService
from life_claims.infrastructure.core_client import CoreClient
from life_claims.infrastructure.sqlite_claims_repository import (
    SQLiteClaimsRepository,
)


def test_claims_service_dependency_builds_components(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "claims.sqlite3"
    monkeypatch.setenv("CLAIMS_DB_PATH", str(database_path))

    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        base_url="http://core.test",
    )

    factory = Mock(return_value=http_client)

    monkeypatch.setattr(
        "life_claims.api.main.create_core_http_client",
        factory,
        raising=False,
    )

    dependency = get_claims_service()

    assert hasattr(dependency, "__next__")

    with dependency_context(dependency) as service:
        assert isinstance(service, ClaimsApplicationService)
        assert isinstance(service.repository, SQLiteClaimsRepository)
        assert service.repository.database_path == database_path
        assert isinstance(service.core_client, CoreClient)
        assert not http_client.is_closed

    factory.assert_called_once_with()
    assert http_client.is_closed


@contextmanager
def dependency_context(generator):
    """Enter and close a generator-based FastAPI dependency."""
    try:
        yield next(generator)
    finally:
        generator.close()
