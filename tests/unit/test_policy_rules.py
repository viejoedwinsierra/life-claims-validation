"""Unit tests for policy existence, identity and coverage rules."""

import pytest
from life_claims.domain.policy_rules import validate_policy


@pytest.fixture
def claim():
    return {
        "documento_asegurado": "123456789",
        "tipo_reclamacion": "MUERTE",
    }


@pytest.fixture
def policy():
    return {
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
    ["ITP", "ENF_GRAVES", "AUX_FUNERARIO"],
)
def test_r5_rejects_uncontracted_coverage(claim, policy, coverage):
    claim["tipo_reclamacion"] = coverage

    assert "R5" in validate_policy(claim, policy)


def test_valid_policy_passes_all_three_rules(claim, policy):
    assert validate_policy(claim, policy) == []
