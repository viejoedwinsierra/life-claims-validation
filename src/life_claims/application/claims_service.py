"""Application service for insurance claims orchestration."""

from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from life_claims.domain.claim_validator import validate_claim


class ClaimsApplicationService:
    """Coordinate claim reservation, validation, and core registration."""

    def __init__(
        self,
        core_client: Any,
        repository: Any,
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        self.core_client = core_client
        self.repository = repository
        self.today_provider = today_provider

    def submit_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        """Reserve, validate, register, and persist a claim."""
        request_id = claim["id_solicitud"]

        reservation = self.repository.reserve_claim(claim)

        if reservation == "PAYLOAD_CONFLICT":
            raise ValueError("Idempotency conflict: request ID has different content")

        if reservation == "ALREADY_EXISTS":
            existing = self.repository.get_by_request_id(request_id)

            if existing is None:
                raise RuntimeError("Reserved claim could not be retrieved")

            return {
                "id_solicitud": existing["id_solicitud"],
                "estado": existing["estado"],
                "numero_siniestro": existing["numero_siniestro"],
                "motivos_rechazo": existing["motivos_rechazo"],
            }

        if reservation == "BUSINESS_DUPLICATE":
            outcome = self.repository.reject_registered_duplicate(claim)

            if outcome == "REJECTED_R8":
                return {
                    "id_solicitud": request_id,
                    "estado": "REJECTED",
                    "numero_siniestro": None,
                    "motivos_rechazo": ["R8"],
                }

            if outcome == "ALREADY_EXISTS":
                existing = self.repository.get_by_request_id(request_id)
                if existing is None:
                    raise RuntimeError("Duplicate claim could not be retrieved")
                return {
                    "id_solicitud": existing["id_solicitud"],
                    "estado": existing["estado"],
                    "numero_siniestro": existing["numero_siniestro"],
                    "motivos_rechazo": existing["motivos_rechazo"],
                }

            if outcome == "PAYLOAD_CONFLICT":
                raise ValueError("Idempotency conflict: request ID has different content")

            if outcome == "EVENT_PENDING":
                return {
                    "id_solicitud": request_id,
                    "estado": "IN_PROGRESS",
                    "numero_siniestro": None,
                    "motivos_rechazo": [],
                }

            raise RuntimeError(f"Unresolved business event: {outcome}")

        if reservation != "CREATED":
            raise RuntimeError(f"Unexpected reservation result: {reservation}")

        policy = self.core_client.get_policy(claim["numero_poliza"])

        existing_claims = self.repository.get_existing_claims(claim["numero_poliza"])

        violations = validate_claim(
            claim=claim,
            policy=policy,
            existing_claims=existing_claims,
            today=self.today_provider(),
        )

        if violations:
            self.repository.save_result(
                id_solicitud=request_id,
                estado="REJECTED",
                motivos_rechazo=violations,
                numero_siniestro=None,
            )

            return {
                "id_solicitud": request_id,
                "estado": "REJECTED",
                "numero_siniestro": None,
                "motivos_rechazo": violations,
            }

        core_payload = {
            "numero_poliza": claim["numero_poliza"],
            "numero_documento_asegurado": claim["asegurado"]["numero_documento"],
            "tipo_reclamacion": claim["tipo_reclamacion"],
            "fecha_siniestro": claim["fecha_siniestro"],
        }

        try:
            core_result = self.core_client.create_claim(
                payload=core_payload,
                idempotency_key=request_id,
            )
        except httpx.TimeoutException:
            self.repository.save_result(
                id_solicitud=request_id,
                estado="PENDING_CONFIRMATION",
                motivos_rechazo=[],
                numero_siniestro=None,
            )

            return {
                "id_solicitud": request_id,
                "estado": "PENDING_CONFIRMATION",
                "numero_siniestro": None,
                "motivos_rechazo": [],
            }

        numero_siniestro = core_result["numero_siniestro"]

        self.repository.save_result(
            id_solicitud=request_id,
            estado="REGISTERED",
            motivos_rechazo=[],
            numero_siniestro=numero_siniestro,
        )

        return {
            "id_solicitud": request_id,
            "estado": "REGISTERED",
            "numero_siniestro": numero_siniestro,
            "motivos_rechazo": [],
        }
