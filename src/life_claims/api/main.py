"""HTTP entry point for the life claims validation service."""

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Response

from life_claims.api.schemas import ClaimRequest
from life_claims.api.structured_logging import StructuredLoggingMiddleware
from life_claims.application.claims_service import ClaimsApplicationService
from life_claims.infrastructure.core_client import CoreClient
from life_claims.infrastructure.core_http_factory import create_core_http_client
from life_claims.infrastructure.sqlite_claims_repository import SQLiteClaimsRepository

app = FastAPI(
    title="Life Claims Validation API",
    description="Digital life insurance claims validation service.",
    version="0.1.0",
)


app.add_middleware(StructuredLoggingMiddleware)

def get_claims_service():
    """Provide the application service and close its HTTP client."""
    repository = get_claims_repository()

    with create_core_http_client() as http_client:
        yield ClaimsApplicationService(
            core_client=CoreClient(http_client),
            repository=repository,
        )


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Report basic application liveness."""
    return {"status": "ok"}


@app.post(
    "/reclamaciones",
    tags=["Claims"],
    responses={
        200: {"description": "Claim rejected by business rules"},
        201: {"description": "Claim registered successfully"},
        202: {"description": "Claim pending confirmation or in progress"},
        409: {"description": "Idempotency conflict"},
        422: {"description": "Invalid request payload"},
        503: {"description": "Claims service unavailable"},
    },
)
def create_claim(
    claim: ClaimRequest,
    response: Response,
    service: Any = Depends(get_claims_service),
) -> dict[str, Any]:
    """Submit a claim to the application service."""
    try:
        result = service.submit_claim(claim.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    status_codes = {
        "REGISTERED": 201,
        "REJECTED": 200,
        "PENDING_CONFIRMATION": 202,
        "IN_PROGRESS": 202,
    }

    estado = result["estado"]

    if estado not in status_codes:
        raise HTTPException(
            status_code=500,
            detail="Unexpected claims service state",
        )

    response.status_code = status_codes[estado]
    return result


def get_claims_repository() -> SQLiteClaimsRepository:
    """Provide the configured SQLite claims repository."""
    database_path = os.environ.get("CLAIMS_DB_PATH")

    if not database_path:
        raise HTTPException(
            status_code=503,
            detail="Claims database is not configured",
        )

    return SQLiteClaimsRepository(database_path)


@app.get(
    "/reclamaciones/{id_solicitud}",
    tags=["Claims"],
    responses={
        200: {"description": "Claim found"},
        404: {"description": "Claim not found"},
        422: {"description": "Invalid request parameters"},
        503: {"description": "Claims database unavailable"},
    },
)
def get_claim(
    id_solicitud: str,
    repository: Any = Depends(get_claims_repository),
) -> dict[str, Any]:
    """Retrieve a previously submitted claim."""
    claim = repository.get_by_request_id(id_solicitud)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )

    return claim
