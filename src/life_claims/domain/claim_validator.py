"""Unified business validation for insurance claims."""

from datetime import date
from typing import Any

from life_claims.domain.claim_normalizer import (
    normalize_claim,
    normalize_policy,
)
from life_claims.domain.date_rules import validate_dates
from life_claims.domain.duplicate_rules import is_duplicate_event
from life_claims.domain.policy_rules import validate_policy


def validate_claim(
    claim: dict[str, Any],
    policy: dict[str, Any] | None,
    existing_claims: list[dict[str, Any]],
    today: date,
) -> list[str]:
    """Evaluate business rules R1-R8 for a claim."""
    normalized_claim = normalize_claim(claim)
    normalized_policy = normalize_policy(policy)

    violations = validate_policy(
        normalized_claim,
        normalized_policy,
    )

    # R1: No policy means date rules cannot be evaluated.
    if normalized_policy is not None:
        violations.extend(
            validate_dates(
                policy=normalized_policy,
                loss_date=normalized_claim["fecha_siniestro"],
                filing_date=normalized_claim["fecha_radicacion"],
                today=today,
            )
        )

    # R8: Compare against previously registered claims.
    if any(
        is_duplicate_event(claim, existing)
        for existing in existing_claims
    ):
        violations.append("R8")

    return violations
