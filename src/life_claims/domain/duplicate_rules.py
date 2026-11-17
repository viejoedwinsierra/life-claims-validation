
"""Business identity rules for duplicate insurance claims."""

from datetime import date
from typing import Any


def event_identity(
    claim: dict[str, Any],
) -> tuple[str, str, str, date, str]:
    """Build a policy-scoped identity for the insured event."""
    insured = claim["asegurado"]
    loss_date = claim["fecha_siniestro"]

    if isinstance(loss_date, str):
        loss_date = date.fromisoformat(loss_date)

    return (
        claim["numero_poliza"],
        insured["tipo_documento"],
        insured["numero_documento"],
        loss_date,
        claim["tipo_reclamacion"],
    )


def is_duplicate_event(
    original: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    """Check whether two claims refer to the same insured event."""
    return event_identity(original) == event_identity(candidate)
