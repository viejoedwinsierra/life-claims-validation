"""Read-only evaluation of insurance claims in batches."""

import sqlite3
from datetime import date
from typing import Any

import httpx

from life_claims.domain.claim_validator import validate_claim


def evaluate_batch(
    claims: list[dict[str, Any]],
    core: Any,
    today: date,
    repository: Any | None = None,
) -> list[dict[str, Any]]:
    """Evaluate claims without registering them in the Core."""
    results = []

    for claim in claims:
        try:
            policy = core.get_policy(claim["numero_poliza"])
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                error_code = f"HTTP_{exc.response.status_code}"
            elif isinstance(exc, httpx.TimeoutException):
                error_code = "TIMEOUT"
            elif isinstance(exc, httpx.ConnectError):
                error_code = "CONNECTION_ERROR"
            else:
                error_code = "REQUEST_ERROR"

            results.append(
                {
                    "id_solicitud": claim["id_solicitud"],
                    "estado": "TECHNICAL_ERROR",
                    "motivos_rechazo": [],
                    "error_tecnico": error_code,
                }
            )
            continue

        try:
            existing_claims = (
                repository.get_existing_claims(claim["numero_poliza"])
                if repository is not None
                else []
            )
        except sqlite3.Error:
            results.append(
                {
                    "id_solicitud": claim["id_solicitud"],
                    "estado": "TECHNICAL_ERROR",
                    "motivos_rechazo": [],
                    "error_tecnico": "REPOSITORY_ERROR",
                }
            )
            continue

        violations = validate_claim(
            claim=claim,
            policy=policy,
            existing_claims=existing_claims,
            today=today,
        )

        results.append(
            {
                "id_solicitud": claim["id_solicitud"],
                "motivos_rechazo": violations,
                "estado": "REJECTED" if violations else "VALID",
            }
        )

    return results
