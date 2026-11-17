"""Normalize external claim and policy contracts."""

from datetime import date
from typing import Any


def normalize_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Normalize a claim received from the external contract."""
    normalized = claim.copy()
    normalized["tipo_documento_asegurado"] = claim["asegurado"]["tipo_documento"]
    normalized["documento_asegurado"] = claim["asegurado"]["numero_documento"]
    normalized["fecha_siniestro"] = date.fromisoformat(claim["fecha_siniestro"])
    normalized["fecha_radicacion"] = date.fromisoformat(
        claim["fecha_radicacion"]
    )

    return normalized


def normalize_policy(
    policy: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Normalize the official core policy contract."""
    if policy is None:
        return None

    normalized = policy.copy()
    normalized["tipo_documento_asegurado"] = policy["tipo_documento_asegurado"]
    normalized["documento_asegurado"] = policy["numero_documento_asegurado"]
    normalized["fecha_inicio"] = date.fromisoformat(
        policy["fecha_inicio_vigencia"]
    )
    normalized["fecha_fin"] = date.fromisoformat(
        policy["fecha_fin_vigencia"]
    )

    change_date = policy.get("fecha_cambio_estado")
    normalized["fecha_cambio_estado"] = (
        date.fromisoformat(change_date)
        if change_date is not None
        else None
    )

    return normalized
