"""Unit tests for the simulated insurance core HTTP client."""

import httpx
import pytest

from life_claims.infrastructure.core_client import CoreClient


def test_get_policy_returns_core_policy():
    """HTTP 200 must return the policy received from the official core."""
    expected_policy = {
        "numero_poliza": "AV-VI-001",
        "estado": "VIGENTE",
        "amparos": ["MUERTE"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/polizas/AV-VI-001"
        return httpx.Response(200, json=expected_policy)

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        result = core.get_policy("AV-VI-001")

    assert result == expected_policy


def test_get_policy_returns_none_on_404():
    """HTTP 404 must represent a nonexistent policy."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/polizas/AV-VI-999"
        return httpx.Response(404, json={"detail": "Policy not found"})

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        result = core.get_policy("AV-VI-999")

    assert result is None


def test_get_policy_raises_http_error_on_503():
    """HTTP 503 must remain a technical error, never a missing policy."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/polizas/AV-VI-001"
        return httpx.Response(503, json={"detail": "Service unavailable"})

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.HTTPStatusError) as error:
            core.get_policy("AV-VI-001")

    assert error.value.response.status_code == 503


def test_get_policy_propagates_timeout():
    """A core timeout must not be interpreted as a nonexistent policy."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Core did not respond within the configured timeout",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
        timeout=3.0,
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.ReadTimeout):
            core.get_policy("AV-VI-001")


def test_get_policy_rejects_non_object_json():
    """A successful response must contain a JSON object."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/polizas/AV-VI-001"
        return httpx.Response(200, json=["invalid", "policy"])

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(ValueError, match="Invalid core policy response"):
            core.get_policy("AV-VI-001")


def test_get_policy_rejects_malformed_json():
    """Malformed JSON must be treated as a technical response error."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/polizas/AV-VI-001"
        return httpx.Response(
            200,
            content=b'{"numero_poliza":',
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(ValueError):
            core.get_policy("AV-VI-001")


def test_create_claim_returns_registered_claim_on_201():
    """HTTP 201 must return the claim registered by the core."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    expected_result = {
        "numero_siniestro": "SIN-20261023-E1C54410",
        "estado_core": "REGISTRADO",
        "fecha_registro": "2026-10-23T14:59:00",
        **payload,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/siniestros"
        assert request.headers["Idempotency-Key"] == "SOL-001"
        assert request.read() == httpx.Request(
            "POST",
            "http://localhost:8081/api/v1/siniestros",
            json=payload,
        ).read()

        return httpx.Response(201, json=expected_result)

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        result = core.create_claim(
            payload=payload,
            idempotency_key="SOL-001",
        )

    assert result == expected_result


def test_create_claim_accepts_idempotent_replay_on_200():
    """An idempotent replay must return the existing core claim."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    existing_claim = {
        "numero_siniestro": "SIN-20261023-E1C54410",
        "estado_core": "REGISTRADO",
        **payload,
    }

    requests_received = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Idempotency-Key"] == "SOL-001"
        requests_received.append(request)
        status_code = 201 if len(requests_received) == 1 else 200
        return httpx.Response(status_code, json=existing_claim)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        first_result = core.create_claim(payload, "SOL-001")
        second_result = core.create_claim(payload, "SOL-001")

    assert first_result == second_result
    assert first_result["numero_siniestro"] == "SIN-20261023-E1C54410"
    assert len(requests_received) == 2


def test_create_claim_raises_conflict_on_409():
    """A reused idempotency key with a different body must fail."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["Idempotency-Key"] == "SOL-001"
        return httpx.Response(
            409,
            json={"detail": "Idempotency key conflict"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.HTTPStatusError) as error:
            core.create_claim(
                payload=payload,
                idempotency_key="SOL-001",
            )

    assert error.value.response.status_code == 409


def test_create_claim_propagates_timeout_without_retry():
    """A POST timeout must propagate without retrying the operation."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    requests_received = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_received.append(request)
        assert request.method == "POST"
        assert request.headers["Idempotency-Key"] == "SOL-001"

        raise httpx.ReadTimeout(
            "Core response timed out",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
        timeout=3.0,
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.ReadTimeout):
            core.create_claim(
                payload=payload,
                idempotency_key="SOL-001",
            )

    assert len(requests_received) == 1


@pytest.mark.parametrize("status_code", [400, 422])
def test_create_claim_propagates_client_errors(status_code):
    """Core validation errors must not be treated as successful registration."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/siniestros"
        return httpx.Response(
            status_code,
            json={"detail": "Core rejected the request"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.HTTPStatusError) as error:
            core.create_claim(
                payload=payload,
                idempotency_key="SOL-001",
            )

    assert error.value.response.status_code == status_code


def test_create_claim_propagates_503_without_retry():
    """Core unavailability must propagate without automatic retries."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }
    requests_received = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_received.append(request)
        assert request.headers["Idempotency-Key"] == "SOL-001"
        return httpx.Response(
            503,
            json={"codigo": "CORE_NO_DISPONIBLE"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(httpx.HTTPStatusError) as error:
            core.create_claim(
                payload=payload,
                idempotency_key="SOL-001",
            )

    assert error.value.response.status_code == 503
    assert len(requests_received) == 1


def test_create_claim_rejects_non_object_json():
    """A successful POST must return a JSON object."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=["invalid", "response"])

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(
            ValueError,
            match="Invalid core claim response",
        ):
            core.create_claim(payload, "SOL-001")


def test_create_claim_rejects_malformed_json():
    """A successful POST with malformed JSON must raise an error."""
    payload = {
        "numero_poliza": "AV-VI-0100000",
        "numero_documento_asegurado": "2123456789",
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            content=b"{invalid-json",
            headers={"Content-Type": "application/json"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:8081",
    ) as http_client:
        core = CoreClient(http_client=http_client)

        with pytest.raises(ValueError):
            core.create_claim(payload, "SOL-001")
