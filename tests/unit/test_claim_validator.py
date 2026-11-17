"""Tests for the unified claim validator."""

from datetime import date

import pytest

from life_claims.domain.claim_validator import validate_claim


def test_valid_claim_has_no_violations():
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

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[],
        today=date(2026, 11, 16),
    )

    assert violations == []


def test_nonexistent_policy_returns_r1_without_date_rule_errors():
    """A missing policy must produce R1 without evaluating policy dates."""
    claim = {
        "id_solicitud": "SOL-002",
        "numero_poliza": "AV-VI-999",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-02",
    }

    violations = validate_claim(
        claim=claim,
        policy=None,
        existing_claims=[],
        today=date(2026, 11, 16),
    )

    assert violations == ["R1"]


@pytest.mark.parametrize(
    ("claim_changes", "policy_changes", "expected_rule"),
    [
        (
            {"asegurado": {
                "tipo_documento": "CE",
                "numero_documento": "123456789",
            }},
            {},
            "R2",
        ),
        (
            {"fecha_siniestro": "2019-12-31"},
            {},
            "R3",
        ),
        (
            {},
            {
                "estado": "CANCELADA",
                "fecha_cambio_estado": "2025-12-31",
            },
            "R4",
        ),
        (
            {"tipo_reclamacion": "ENF_GRAVES"},
            {},
            "R5",
        ),
        (
            {"fecha_siniestro": "2023-01-01"},
            {},
            "R6",
        ),
        (
            {"fecha_siniestro": "2026-12-01"},
            {},
            "R7",
        ),
    ],
)
def test_unified_validator_detects_business_rule(
    claim_changes,
    policy_changes,
    expected_rule,
):
    """The unified validator must execute the underlying business rules."""
    claim = {
        "id_solicitud": "SOL-003",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-02",
    }

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

    claim.update(claim_changes)
    policy.update(policy_changes)

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[],
        today=date(2026, 11, 16),
    )

    assert expected_rule in violations


def test_unified_validator_rejects_duplicate_event():
    """R8 must detect the same insured event with a different request ID."""
    claim = {
        "id_solicitud": "SOL-002",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-03",
    }

    existing_claim = {
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

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[existing_claim],
        today=date(2026, 11, 16),
    )

    assert violations == ["R8"]


def test_unified_validator_reports_multiple_violations():
    """The validator must report all applicable business violations."""
    claim = {
        "id_solicitud": "SOL-004",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CE",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "ENF_GRAVES",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-02",
    }

    policy = {
        "numero_poliza": "AV-VI-001",
        "tipo_documento_asegurado": "CC",
        "numero_documento_asegurado": "123456789",
        "fecha_inicio_vigencia": "2020-01-01",
        "fecha_fin_vigencia": "2030-01-01",
        "estado": "CANCELADA",
        "fecha_cambio_estado": "2025-12-31",
        "amparos": ["MUERTE", "ITP"],
    }

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[],
        today=date(2026, 11, 16),
    )

    assert set(violations) == {"R2", "R4", "R5"}
    assert len(violations) == 3


@pytest.mark.parametrize(
    ("filing_date", "expected_violations"),
    [
        ("2025-12-31", []),       # Day 730: accepted
        ("2026-01-01", ["R6"]),   # Day 731: rejected
    ],
)
def test_r6_filing_deadline_boundary(filing_date, expected_violations):
    """A claim is timely through day 730 and late on day 731."""
    claim = {
        "id_solicitud": "SOL-R6",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2024-01-01",
        "fecha_radicacion": filing_date,
    }

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

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[],
        today=date(2026, 11, 16),
    )

    assert violations == expected_violations


def test_r8_detects_duplicate_with_date_object():
    """R8 must compare equivalent ISO strings and date objects."""
    claim = {
        "id_solicitud": "SOL-NEW",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": "2026-01-01",
        "fecha_radicacion": "2026-01-03",
    }

    existing_claim = {
        "id_solicitud": "SOL-OLD",
        "numero_poliza": "AV-VI-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "tipo_reclamacion": "MUERTE",
        "fecha_siniestro": date(2026, 1, 1),
        "fecha_radicacion": date(2026, 1, 2),
    }

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

    violations = validate_claim(
        claim=claim,
        policy=policy,
        existing_claims=[existing_claim],
        today=date(2026, 11, 16),
    )

    assert violations == ["R8"]
