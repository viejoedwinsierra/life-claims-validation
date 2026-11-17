"""Pure business rules for insurance policy validation."""

from typing import Any


def validate_policy(
    claim: dict[str, Any],
    policy: dict[str, Any] | None,
) -> list[str]:
    """Validate policy existence, insured identity and coverage."""
    violations: list[str] = []

    # R1: Policy does not exist in the official core.
    if policy is None:
        return ["R1"]

    # R2: Both document type and number must be present and match.
    claim_type = claim.get("tipo_documento_asegurado")
    policy_type = policy.get("tipo_documento_asegurado")
    claim_number = claim.get("documento_asegurado")
    policy_number = policy.get("documento_asegurado")

    if (
        not claim_type
        or not policy_type
        or not claim_number
        or not policy_number
        or claim_type != policy_type
        or claim_number != policy_number
    ):
        violations.append("R2")

    # R5: Requested coverage must be contracted.
    if claim["tipo_reclamacion"] not in policy["amparos"]:
        violations.append("R5")

    return violations
