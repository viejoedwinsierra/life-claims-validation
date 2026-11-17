"""Unit tests for policy existence, identity and coverage rules."""

import pytest

from life_claims.domain.policy_rules import validate_policy


@pytest.fixture
def claim():
    return {
        "tipo_documento_asegurado": "CC",
        "documento_asegurado": "123456789",
        "tipo_reclamacion": "MUERTE",
    }


@pytest.fixture
def policy():
    return {
        "tipo_documento_asegurado": "CC",
        "documento_asegurado": "123456789",
        "amparos": ["MUERTE", "ITP"],
    }


def test_r1_rejects_nonexistent_policy(claim):
    assert "R1" in validate_policy(claim, None)


def test_r2_rejects_document_mismatch(claim, policy):
    policy["documento_asegurado"] = "987654321"

    assert "R2" in validate_policy(claim, policy)


@pytest.mark.parametrize(
    "coverage",
    ["ENF_GRAVES", "AUX_FUNERARIO"],
)
def test_r5_rejects_uncontracted_coverage(claim, policy, coverage):
    claim["tipo_reclamacion"] = coverage

    assert "R5" in validate_policy(claim, policy)


@pytest.mark.parametrize(
    "coverage",
    ["MUERTE", "ITP"],
)
def test_r5_accepts_contracted_coverage(claim, policy, coverage):
    claim["tipo_reclamacion"] = coverage

    assert "R5" not in validate_policy(claim, policy)


def test_valid_policy_passes_all_three_rules(claim, policy):
    assert validate_policy(claim, policy) == []


def test_r2_rejects_different_document_type():
    """R2 must compare both document type and document number."""
    claim = {
        "documento_asegurado": "123456789",
        "tipo_documento_asegurado": "CE",
        "tipo_reclamacion": "MUERTE",
    }
    policy = {
        "documento_asegurado": "123456789",
        "tipo_documento_asegurado": "CC",
        "amparos": ["MUERTE"],
    }

    assert "R2" in validate_policy(claim, policy)


def test_r2_rejects_missing_document_type():
    """R2 must reject an incomplete insured identity."""
    claim = {
        "documento_asegurado": "123456789",
        "tipo_reclamacion": "MUERTE",
    }
    policy = {
        "documento_asegurado": "123456789",
        "tipo_documento_asegurado": "CC",
        "amparos": ["MUERTE"],
    }

    assert "R2" in validate_policy(claim, policy)


def test_r2_rejects_missing_document_type_on_both_sides():
    """R2 must reject identities missing document types on both sides."""
    claim = {
        "documento_asegurado": "123456789",
        "tipo_reclamacion": "MUERTE",
    }
    policy = {
        "documento_asegurado": "123456789",
        "amparos": ["MUERTE"],
    }

    assert "R2" in validate_policy(claim, policy)
