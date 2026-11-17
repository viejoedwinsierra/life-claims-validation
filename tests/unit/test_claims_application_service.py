"""Unit tests for claims application orchestration."""

from datetime import date
from unittest.mock import Mock

from life_claims.application.claims_service import ClaimsApplicationService


def test_submit_claim_rejects_missing_policy_without_core_registration():
    """A missing policy must produce R1 without registering a claim."""
    core = Mock()
    core.get_policy.return_value = None

    repository = Mock()
    repository.reserve_claim.return_value = "CREATED"
    repository.get_existing_claims.return_value = []

    service = ClaimsApplicationService(
        core_client=core,
        repository=repository,
        today_provider=lambda: date(2026, 11, 16),
    )

    claim = {
        "id_solicitud": "SOL-TEST-005-001",
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

    result = service.submit_claim(claim)

    assert result["id_solicitud"] == "SOL-TEST-005-001"
    assert result["estado"] == "REJECTED"
    assert result["numero_siniestro"] is None
    assert "R1" in result["motivos_rechazo"]

    core.get_policy.assert_called_once_with("AV-VI-NO-EXISTE")
    core.create_claim.assert_not_called()


def test_submit_claim_rejects_insured_document_mismatch():
    """R2 must reject a mismatched insured document."""
    core = Mock()
    core.get_policy.return_value = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "9999999999",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }

    repository = Mock()
    repository.reserve_claim.return_value = "CREATED"
    repository.get_existing_claims.return_value = []

    service = ClaimsApplicationService(
        core_client=core,
        repository=repository,
        today_provider=lambda: date(2026, 11, 16),
    )

    claim = {
        "id_solicitud": "SOL-TEST-005-002",
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

    result = service.submit_claim(claim)

    assert result["id_solicitud"] == "SOL-TEST-005-002"
    assert result["estado"] == "REJECTED"
    assert result["numero_siniestro"] is None
    assert "R2" in result["motivos_rechazo"]

    core.get_policy.assert_called_once_with("AV-VI-0100000")
    core.create_claim.assert_not_called()


def test_submit_claim_registers_valid_claim_in_core():
    """A valid claim must be registered using the core contract."""
    core = Mock()
    core.get_policy.return_value = {
        "numero_poliza": "AV-VI-0100000",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "2123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-12-31",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE"],
    }
    core.create_claim.return_value = {
        "numero_siniestro": "SIN-20261116-TEST0001",
        "estado_core": "REGISTRADO",
    }

    repository = Mock()
    repository.reserve_claim.return_value = "CREATED"
    repository.get_existing_claims.return_value = []

    service = ClaimsApplicationService(
        core_client=core,
        repository=repository,
        today_provider=lambda: date(2026, 11, 16),
    )

    claim = {
        "id_solicitud": "SOL-TEST-005-003",
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

    result = service.submit_claim(claim)

    assert result["id_solicitud"] == "SOL-TEST-005-003"
    assert result["estado"] == "REGISTERED"
    assert result["numero_siniestro"] == "SIN-20261116-TEST0001"
    assert result["motivos_rechazo"] == []

    core.create_claim.assert_called_once_with(
        payload={
            "numero_poliza": "AV-VI-0100000",
            "numero_documento_asegurado": "2123456789",
            "tipo_reclamacion": "MUERTE",
            "fecha_siniestro": "2026-01-01",
        },
        idempotency_key="SOL-TEST-005-003",
    )
