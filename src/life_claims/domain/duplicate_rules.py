
"""Provisional claim duplicate detection rules."""

from typing import Any


def event_identity(claim: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Build a policy-scoped claim identity."""
    insured = claim["asegurado"]

    return (
        claim["numero_poliza"],
        insured["tipo_documento"],
        insured["numero_documento"],
        claim["fecha_siniestro"],
        claim["tipo_reclamacion"],
    )


def is_duplicate_event(
    original: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    """Check whether two claims have the same policy-scoped identity."""
    return event_identity(original) == event_identity(candidate)
