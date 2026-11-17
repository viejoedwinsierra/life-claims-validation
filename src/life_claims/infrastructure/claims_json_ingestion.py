"""Lossless and idempotent ingestion of analytical claim requests."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "datos/migrations/003_create_claims_analytics.sql"
)


def ingest_claims_json(
    source_path: str | Path,
    database_path: str | Path,
) -> dict[str, int]:
    """Ingest a JSON array without losing duplicate source records."""
    source_path = Path(source_path)
    database_path = Path(database_path)

    raw_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(raw_bytes).hexdigest()
    records = json.loads(raw_bytes.decode("utf-8"))

    if not isinstance(records, list):
        raise ValueError("Claims JSON root must be an array")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Every claim must be a JSON object")

    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path, timeout=10) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))

        existing = connection.execute(
            """
            SELECT batch_id
            FROM claims_ingestion_batches
            WHERE source_sha256 = ?
            """,
            (source_hash,),
        ).fetchone()

        if existing is not None:
            return {"rows_inserted": 0}

        cursor = connection.execute(
            """
            INSERT INTO claims_ingestion_batches (
                source_filename,
                source_sha256,
                rows_inserted
            )
            VALUES (?, ?, ?)
            """,
            (source_path.name, source_hash, len(records)),
        )

        batch_id = cursor.lastrowid

        rows: list[tuple[Any, ...]] = []

        for position, claim in enumerate(records, start=1):
            rows.append(
                (
                    batch_id,
                    position,
                    claim.get("id_solicitud"),
                    claim.get("numero_poliza"),
                    claim.get("canal"),
                    claim.get("tipo_reclamacion"),
                    claim.get("fecha_siniestro"),
                    claim.get("fecha_radicacion"),
                    json.dumps(claim, ensure_ascii=False, sort_keys=True),
                )
            )

        connection.executemany(
            """
            INSERT INTO reclamaciones_analytics (
                batch_id,
                source_row_number,
                id_solicitud,
                numero_poliza,
                canal,
                tipo_reclamacion,
                fecha_siniestro,
                fecha_radicacion,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return {"rows_inserted": len(records)}
