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

    # R2: Insured document must match the policy.
    if claim["documento_asegurado"] != policy["documento_asegurado"]:
        violations.append("R2")

    # R5: Requested coverage must be contracted.
    if claim["tipo_reclamacion"] not in policy["amparos"]:
        violations.append("R5")

    return violations
