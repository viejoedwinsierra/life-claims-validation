"""Business rules for insurance claim dates."""

from datetime import date
from typing import Any


def validate_dates(
    policy: dict[str, Any],
    loss_date: date,
    filing_date: date,
    today: date,
) -> list[str]:
    """Return violated business rule identifiers.

    R3: Loss date must be within policy validity, inclusive.
    R4: Cancellation or suspension effective on/before loss rejects.
    R6: Filing must occur within 730 days after loss.
    R7: Loss cannot be future or later than filing.
    """
    violations: list[str] = []

    # R3 - Policy validity boundaries are inclusive.
    if not (
        policy["fecha_inicio"]
        <= loss_date
        <= policy["fecha_fin"]
    ):
        violations.append("R3")

    # R4 - Policy status effective on loss date.
    if policy["estado"] in {"CANCELADA", "SUSPENDIDA"}:
        change_date = policy.get("fecha_cambio_estado")

        if change_date is not None and change_date <= loss_date:
            violations.append("R4")

    # R6 - Filing deadline.
    elapsed_days = (filing_date - loss_date).days

    if elapsed_days > 730:
        violations.append("R6")

    # R7 - Future loss or filing before loss.
    if loss_date > today or loss_date > filing_date:
        violations.append("R7")

    return violations
