"""SQLite persistence for insurance claim requests."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from life_claims.domain.duplicate_rules import event_identity


class SQLiteClaimsRepository:
    """Persist claims with request-level idempotency."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _serialize_claim(claim: dict[str, Any]) -> str:
        return json.dumps(
            claim,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def reserve_claim(self, claim: dict[str, Any]) -> str:
        """Atomically reserve a request and its insured business event."""
        payload_json = self._serialize_claim(claim)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        identity = event_identity(claim)
        identity_json = json.dumps(
            [value.isoformat() if hasattr(value, "isoformat") else value for value in identity],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        business_event_key = hashlib.sha256(identity_json.encode("utf-8")).hexdigest()

        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            cursor = connection.execute(
                """
                INSERT INTO reclamaciones (
                    id_solicitud,
                    payload_hash,
                    business_event_key,
                    numero_poliza,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    claim["id_solicitud"],
                    payload_hash,
                    business_event_key,
                    claim["numero_poliza"],
                    payload_json,
                ),
            )

            if cursor.rowcount == 1:
                return "CREATED"

            existing_request = connection.execute(
                """
                SELECT payload_hash
                FROM reclamaciones
                WHERE id_solicitud = ?
                """,
                (claim["id_solicitud"],),
            ).fetchone()

            if existing_request is not None:
                if existing_request[0] == payload_hash:
                    return "ALREADY_EXISTS"
                return "PAYLOAD_CONFLICT"

            existing_event = connection.execute(
                """
                SELECT id_solicitud
                FROM reclamaciones
                WHERE business_event_key = ?
                  AND estado IN (
                      'RECEIVED',
                      'REGISTERED',
                      'PENDING_CONFIRMATION',
                      'TECHNICAL_ERROR'
                  )
                """,
                (business_event_key,),
            ).fetchone()

            if existing_event is not None:
                return "BUSINESS_DUPLICATE"

            raise RuntimeError("Business event reservation could not be verified")

    def reject_registered_duplicate(
        self,
        claim: dict[str, Any],
    ) -> str:
        """Persist an R8 rejection only when the original is registered."""
        payload_json = self._serialize_claim(claim)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        identity_json = json.dumps(
            [
                value.isoformat() if hasattr(value, "isoformat") else value
                for value in event_identity(claim)
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        business_event_key = hashlib.sha256(identity_json.encode("utf-8")).hexdigest()

        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT payload_hash
                FROM reclamaciones
                WHERE id_solicitud = ?
                """,
                (claim["id_solicitud"],),
            ).fetchone()

            if existing is not None:
                if existing[0] == payload_hash:
                    return "ALREADY_EXISTS"
                return "PAYLOAD_CONFLICT"

            original = connection.execute(
                """
                SELECT estado
                FROM reclamaciones
                WHERE business_event_key = ?
                  AND estado IN (
                      'RECEIVED',
                      'REGISTERED',
                      'PENDING_CONFIRMATION',
                      'TECHNICAL_ERROR'
                  )
                """,
                (business_event_key,),
            ).fetchone()

            if original is None:
                return "RETRY_RESERVATION"

            if original[0] != "REGISTERED":
                return "EVENT_PENDING"

            connection.execute(
                """
                INSERT INTO reclamaciones (
                    id_solicitud,
                    payload_hash,
                    business_event_key,
                    numero_poliza,
                    payload_json,
                    estado,
                    motivos_rechazo_json
                )
                VALUES (?, ?, NULL, ?, ?, 'REJECTED', ?)
                """,
                (
                    claim["id_solicitud"],
                    payload_hash,
                    claim["numero_poliza"],
                    payload_json,
                    json.dumps(["R8"]),
                ),
            )

            return "REJECTED_R8"

    def save_result(
        self,
        id_solicitud: str,
        estado: str,
        motivos_rechazo: list[str],
        numero_siniestro: str | None,
    ) -> None:
        """Persist the outcome of a previously reserved claim."""
        allowed_states = {
            "REJECTED",
            "REGISTERED",
            "PENDING_CONFIRMATION",
            "TECHNICAL_ERROR",
        }

        if estado not in allowed_states:
            raise ValueError(f"Unsupported result state: {estado}")

        with sqlite3.connect(self.database_path, timeout=10) as connection:
            cursor = connection.execute(
                """
                UPDATE reclamaciones
                SET estado = ?,
                    motivos_rechazo_json = ?,
                    numero_siniestro = ?,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id_solicitud = ?
                  AND estado = 'RECEIVED'
                """,
                (
                    estado,
                    json.dumps(motivos_rechazo),
                    numero_siniestro,
                    id_solicitud,
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError("Claim does not exist or is not in RECEIVED state")

    def get_by_request_id(
        self,
        id_solicitud: str,
    ) -> dict[str, Any] | None:
        """Retrieve the persisted outcome of a claim."""
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row

            row = connection.execute(
                """
                SELECT
                    id_solicitud,
                    numero_poliza,
                    estado,
                    motivos_rechazo_json,
                    numero_siniestro
                FROM reclamaciones
                WHERE id_solicitud = ?
                """,
                (id_solicitud,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id_solicitud": row["id_solicitud"],
            "numero_poliza": row["numero_poliza"],
            "estado": row["estado"],
            "motivos_rechazo": json.loads(row["motivos_rechazo_json"]),
            "numero_siniestro": row["numero_siniestro"],
        }

    def get_existing_claims(
        self,
        numero_poliza: str,
    ) -> list[dict[str, Any]]:
        """Return registered claims for business duplicate validation."""
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM reclamaciones
                WHERE numero_poliza = ?
                  AND estado = 'REGISTERED'
                ORDER BY fecha_creacion, id_solicitud
                """,
                (numero_poliza,),
            ).fetchall()

        return [json.loads(row[0]) for row in rows]
