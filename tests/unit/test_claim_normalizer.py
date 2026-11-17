"""Tests for mapping external contracts to domain inputs."""

from datetime import date

from life_claims.domain.claim_normalizer import (
    normalize_claim,
    normalize_policy,
)


def test_normalize_claim():
    claim = {
        "id_solicitud": "SOL-001",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-02",
    }

    normalized = normalize_claim(claim)

    assert normalized["documento_asegurado"] == "123456789"
    assert normalized["tipo_reclamacion"] == "MUERTE"
    assert normalized["fecha_siniestro"] == date(2026, 1, 1)
    assert normalized["fecha_radicacion"] == date(2026, 1, 2)
    assert normalized["tipo_documento_asegurado"] == "CC"

def test_normalize_policy():
    policy = {
        "numero_poliza": "AV-VI-001",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-01-01",
        "estado": "VIGENTE",
        "fecha_cambio_estado": "2020-01-01",
        "amparos": ["MUERTE", "ITP"],
    }

    normalized = normalize_policy(policy)

    assert normalized["documento_asegurado"] == "123456789"
    assert normalized["fecha_inicio"] == date(2020, 1, 1)
    assert normalized["fecha_fin"] == date(2030, 1, 1)
    assert normalized["fecha_cambio_estado"] == date(2020, 1, 1)
    assert normalized["estado"] == "VIGENTE"
    assert normalized["amparos"] == ["MUERTE", "ITP"]
    assert normalized["tipo_documento_asegurado"] == "CC"

def test_normalize_missing_policy():
    """A missing policy must remain None for rule R1."""
    assert normalize_policy(None) is None
