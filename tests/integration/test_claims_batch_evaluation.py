"""Tests for read-only batch evaluation of claims."""

from datetime import date
from typing import Any

from life_claims.application.claims_batch_evaluator import evaluate_batch


class ReadOnlyCore:
    """Simulate policy lookups without registering claims."""

    def __init__(self, policies: dict[str, dict[str, Any]]) -> None:
        self.policies = policies
        self.lookups = 0
        self.registrations = 0

    def get_policy(self, policy_number: str) -> dict[str, Any] | None:
        self.lookups += 1
        return self.policies.get(policy_number)

    def create_claim(self, **kwargs: Any) -> None:
        self.registrations += 1
        raise AssertionError("Batch evaluation must not register claims")



def test_batch_evaluation_does_not_register_claims():
    core = ReadOnlyCore(policies={})

    claims = [
        {
            "id_solicitud": "TEST-001",
            "numero_poliza": "POL-NOT-FOUND-001",
            "asegurado": {"tipo_documento": "CC", "numero_documento": "123456789"},
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2026-01-01",
            "fecha_radicacion": "2026-01-15",
        },
        {
            "id_solicitud": "TEST-002",
            "numero_poliza": "POL-NOT-FOUND-002",
            "asegurado": {"tipo_documento": "CC", "numero_documento": "987654321"},
            "tipo_reclamacion": "ITP",
            "fecha_siniestro": "2026-02-01",
            "fecha_radicacion": "2026-02-10",
        },
    ]

    results = evaluate_batch(
        claims=claims,
        core=core,
        today=date(2026, 11, 17),
    )

    assert len(results) == 2
    assert all(result["estado"] == "REJECTED" for result in results)
    assert all("R1" in result["motivos_rechazo"] for result in results)
    assert core.lookups == 2
    assert core.registrations == 0


def test_valid_claim_does_not_register_in_core():
    """A valid claim must remain read-only during batch evaluation."""
    policy = {
        "numero_poliza": "POL-VALID-001",
        "producto": "VIDA_INDIVIDUAL",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE", "ITP"],
        "valor_asegurado": 30000000,
    }

    claim = {
        "id_solicitud": "TEST-VALID-001",
        "numero_poliza": "POL-VALID-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-15",
    }

    core = ReadOnlyCore(
        policies={"POL-VALID-001": policy}
    )

    results = evaluate_batch(
        claims=[claim],
        core=core,
        today=date(2026, 11, 17),
    )

    assert len(results) == 1
    assert results[0]["estado"] == "VALID"
    assert results[0]["motivos_rechazo"] == []
    assert core.lookups == 1
    assert core.registrations == 0


def test_batch_continues_after_core_http_503():
    """A Core outage must not stop the remaining evaluations."""
    import httpx

    class IntermittentCore:
        def __init__(self):
            self.lookups = []
            self.registrations = 0

        def get_policy(self, policy_number):
            self.lookups.append(policy_number)

            if policy_number == "POL-UNAVAILABLE":
                request = httpx.Request(
                    "GET",
                    "http://core.test/api/v1/polizas/POL-UNAVAILABLE",
                )
                response = httpx.Response(
                    503,
                    request=request,
                )
                raise httpx.HTTPStatusError(
                    "Core unavailable",
                    request=request,
                    response=response,
                )

            return None

        def create_claim(self, **kwargs):
            self.registrations += 1
            raise AssertionError("Read-only evaluator registered a claim")

    claims = [
        {
            "id_solicitud": "TEST-503",
            "numero_poliza": "POL-UNAVAILABLE",
        },
        {
            "id_solicitud": "TEST-R1",
            "numero_poliza": "POL-NOT-FOUND",
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "123456789",
            },
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2026-01-01",
            "fecha_radicacion": "2026-01-15",
        },
    ]

    core = IntermittentCore()

    results = evaluate_batch(
        claims=claims,
        core=core,
        today=date(2026, 11, 17),
    )

    assert len(results) == 2

    assert results[0] == {
        "id_solicitud": "TEST-503",
        "estado": "TECHNICAL_ERROR",
        "motivos_rechazo": [],
        "error_tecnico": "HTTP_503",
    }

    assert results[1]["estado"] == "REJECTED"
    assert "R1" in results[1]["motivos_rechazo"]

    assert core.lookups == [
        "POL-UNAVAILABLE",
        "POL-NOT-FOUND",
    ]
    assert core.registrations == 0


def test_batch_continues_after_core_timeout():
    """A Core timeout must not stop subsequent claim evaluations."""
    import httpx

    class TimeoutCore:
        def __init__(self):
            self.lookups = []
            self.registrations = 0

        def get_policy(self, policy_number):
            self.lookups.append(policy_number)

            if policy_number == "POL-TIMEOUT":
                request = httpx.Request(
                    "GET",
                    "http://core.test/api/v1/polizas/POL-TIMEOUT",
                )
                raise httpx.ReadTimeout(
                    "Core response timed out",
                    request=request,
                )

            return None

        def create_claim(self, **kwargs):
            self.registrations += 1
            raise AssertionError("Read-only evaluation must not register")

    claims = [
        {
            "id_solicitud": "TEST-TIMEOUT",
            "numero_poliza": "POL-TIMEOUT",
        },
        {
            "id_solicitud": "TEST-AFTER-TIMEOUT",
            "numero_poliza": "POL-MISSING",
            "asegurado": {
                "tipo_documento": "CC",
                "numero_documento": "123456789",
            },
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2026-01-01",
            "fecha_radicacion": "2026-01-15",
        },
    ]

    core = TimeoutCore()

    results = evaluate_batch(
        claims=claims,
        core=core,
        today=date(2026, 11, 17),
    )

    assert len(results) == 2

    assert results[0] == {
        "id_solicitud": "TEST-TIMEOUT",
        "estado": "TECHNICAL_ERROR",
        "motivos_rechazo": [],
        "error_tecnico": "TIMEOUT",
    }

    assert results[1]["estado"] == "REJECTED"
    assert "R1" in results[1]["motivos_rechazo"]

    assert core.lookups == [
        "POL-TIMEOUT",
        "POL-MISSING",
    ]
    assert core.registrations == 0


def test_batch_records_technical_error_details():
    """Technical failures must retain a diagnostic error category."""
    import httpx

    class FailingCore:
        def get_policy(self, policy_number):
            request = httpx.Request(
                "GET",
                f"http://core.test/api/v1/polizas/{policy_number}",
            )

            if policy_number == "POL-503":
                response = httpx.Response(
                    503,
                    request=request,
                )
                raise httpx.HTTPStatusError(
                    "Core unavailable",
                    request=request,
                    response=response,
                )

            raise httpx.ReadTimeout(
                "Core timeout",
                request=request,
            )

    claims = [
        {
            "id_solicitud": "TEST-503",
            "numero_poliza": "POL-503",
        },
        {
            "id_solicitud": "TEST-TIMEOUT",
            "numero_poliza": "POL-TIMEOUT",
        },
    ]

    results = evaluate_batch(
        claims=claims,
        core=FailingCore(),
        today=date(2026, 11, 17),
    )

    assert len(results) == 2

    assert results[0]["estado"] == "TECHNICAL_ERROR"
    assert results[0]["error_tecnico"] == "HTTP_503"

    assert results[1]["estado"] == "TECHNICAL_ERROR"
    assert results[1]["error_tecnico"] == "TIMEOUT"

    assert all(
        result["motivos_rechazo"] == []
        for result in results
    )


def test_batch_records_connection_error():
    """Connection failures must be classified as technical errors."""
    import httpx

    class DisconnectedCore:
        def get_policy(self, policy_number):
            request = httpx.Request(
                "GET",
                f"http://core.test/api/v1/polizas/{policy_number}",
            )
            raise httpx.ConnectError(
                "Connection refused",
                request=request,
            )

    results = evaluate_batch(
        claims=[
            {
                "id_solicitud": "TEST-CONNECTION",
                "numero_poliza": "POL-CONNECTION",
            }
        ],
        core=DisconnectedCore(),
        today=date(2026, 11, 17),
    )

    assert results == [
        {
            "id_solicitud": "TEST-CONNECTION",
            "estado": "TECHNICAL_ERROR",
            "motivos_rechazo": [],
            "error_tecnico": "CONNECTION_ERROR",
        }
    ]


def test_batch_detects_r8_against_registered_claims():
    """Read-only evaluation must detect registered duplicate events."""

    policy = {
        "numero_poliza": "AV-VI-001",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-01-01",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }

    existing_claim = {
        "id_solicitud": "SOL-REGISTERED",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-02",
        "canal": "WEB",
    }

    new_claim = {
        **existing_claim,
        "id_solicitud": "SOL-NEW",
        "fecha_radicacion": "2026-01-03",
        "canal": "APP",
    }

    class ReadOnlyCore:
        def get_policy(self, policy_number):
            assert policy_number == "AV-VI-001"
            return policy

        def create_claim(self, **kwargs):
            raise AssertionError("Core registration is forbidden")

    class RegisteredClaimsRepository:
        def __init__(self):
            self.lookups = []

        def get_existing_claims(self, policy_number):
            self.lookups.append(policy_number)
            return [existing_claim]

    repository = RegisteredClaimsRepository()

    results = evaluate_batch(
        claims=[new_claim],
        core=ReadOnlyCore(),
        today=date(2026, 11, 17),
        repository=repository,
    )

    assert results == [
        {
            "id_solicitud": "SOL-NEW",
            "motivos_rechazo": ["R8"],
            "estado": "REJECTED",
        }
    ]

    assert repository.lookups == ["AV-VI-001"]


def test_batch_does_not_ignore_repository_failure():
    """A repository failure must not produce a false VALID result."""
    import sqlite3

    class AvailableCore:
        def get_policy(self, policy_number):
            return {
                "numero_poliza": policy_number,
                "tipo_documento_asegurado": "CC",
                "numero_documento_asegurado": "123456789",
                "fecha_inicio_vigencia": "2020-01-01",
                "fecha_fin_vigencia": "2030-01-01",
                "estado": "VIGENTE",
                "fecha_cambio_estado": "2020-01-01",
                "amparos": ["MUERTE"],
            }

        def create_claim(self, **kwargs):
            raise AssertionError("Core registration is forbidden")

    class FailingRepository:
        def get_existing_claims(self, policy_number):
            raise sqlite3.OperationalError(
                "Database is temporarily unavailable"
            )

    claim = {
        "id_solicitud": "SOL-DB-ERROR",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-03",
        "canal": "WEB",
    }

    results = evaluate_batch(
        claims=[claim],
        core=AvailableCore(),
        today=date(2026, 11, 17),
        repository=FailingRepository(),
    )

    assert results == [
        {
            "id_solicitud": "SOL-DB-ERROR",
            "estado": "TECHNICAL_ERROR",
            "motivos_rechazo": [],
            "error_tecnico": "REPOSITORY_ERROR",
        }
    ]
