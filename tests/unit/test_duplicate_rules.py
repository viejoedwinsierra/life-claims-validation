"""Tests for duplicate claim detection (R8)."""

import pytest

from life_claims.domain.duplicate_rules import is_duplicate_event


@pytest.fixture
def original_claim():
    return {
        "id_solicitud": "SOL-001",
        "numero_poliza": "POL-001",
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "123456789",
        },
        "fecha_siniestro": "2026-01-01",
        "tipo_reclamacion": "MUERTE",
        "canal": "WEB",
    }


def test_r8_detects_duplicate_across_channels(original_claim):
    other = {
        **original_claim,
        "id_solicitud": "SOL-002",
        "canal": "APP",
    }

    assert is_duplicate_event(original_claim, other)


def test_r8_allows_different_policy(original_claim):
    other = {**original_claim, "numero_poliza": "POL-002"}

    assert not is_duplicate_event(original_claim, other)


def test_r8_allows_different_insured(original_claim):
    other = {
        **original_claim,
        "asegurado": {
            "tipo_documento": "CC",
            "numero_documento": "987654321",
        },
    }

    assert not is_duplicate_event(original_claim, other)


def test_r8_allows_different_event_date(original_claim):
    other = {**original_claim, "fecha_siniestro": "2026-01-02"}

    assert not is_duplicate_event(original_claim, other)


def test_r8_allows_different_claim_type(original_claim):
    other = {**original_claim, "tipo_reclamacion": "ITP"}

    assert not is_duplicate_event(original_claim, other)


def test_r8_distinguishes_document_types(original_claim):
    other = {
        **original_claim,
        "asegurado": {
            "tipo_documento": "CE",
            "numero_documento": "123456789",
        },
    }

    assert not is_duplicate_event(original_claim, other)
