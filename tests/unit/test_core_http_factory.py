"""Tests for the insurance core HTTP client factory."""

import httpx

from life_claims.infrastructure.core_http_factory import (
    create_core_http_client,
)


def test_create_core_http_client_uses_configured_url_and_timeouts(
    monkeypatch,
):
    """The core connection must use explicit configuration."""
    monkeypatch.setenv(
        "CORE_BASE_URL",
        "http://localhost:8081",
    )

    with create_core_http_client() as client:
        assert isinstance(client, httpx.Client)

        assert str(client.base_url) == (
            "http://localhost:8081"
        )

        assert client.timeout.connect == 3.0
        assert client.timeout.read == 5.0
        assert client.timeout.write == 3.0
        assert client.timeout.pool == 3.0
