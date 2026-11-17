"""Lossless and idempotent policy CSV ingestion into SQLite."""

import csv
import hashlib
import sqlite3
from pathlib import Path

POLICY_COLUMNS = (
    "numero_poliza",
    "producto",
    "tipo_documento_asegurado",
    "numero_documento_asegurado",
    "nombre_asegurado",
    "fecha_nacimiento",
    "fecha_inicio_vigencia",
    "fecha_fin_vigencia",
    "estado",
    "fecha_cambio_estado",
    "amparos",
    "valor_asegurado",
    "canal_venta",
    "ciudad",
    "fecha_actualizacion",
)

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3] / "datos" / "migrations" / "002_create_policy_raw.sql"
)


def ingest_policy_csv(
    csv_path: str | Path,
    database_path: str | Path,
) -> dict[str, int]:
    """Load every CSV row once per file content hash."""
    source = Path(csv_path)
    database = Path(database_path)

    content = source.read_bytes()
    source_hash = hashlib.sha256(content).hexdigest()

    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if tuple(reader.fieldnames or ()) != POLICY_COLUMNS:
            raise ValueError("Unexpected policy CSV columns")

        rows = list(reader)

        if any(None in row for row in rows):
            raise ValueError("CSV contains unexpected extra fields")

    database.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))

        existing = connection.execute(
            """
            SELECT batch_id
            FROM ingestion_batches
            WHERE source_sha256 = ?
            """,
            (source_hash,),
        ).fetchone()

        if existing is not None:
            return {"rows_inserted": 0}

        with connection:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_batches (
                    source_filename,
                    source_sha256,
                    rows_inserted
                )
                VALUES (?, ?, ?)
                """,
                (source.name, source_hash, len(rows)),
            )

            batch_id = cursor.lastrowid

            columns = (
                "batch_id",
                "source_row_number",
                *POLICY_COLUMNS,
            )

            placeholders = ", ".join("?" for _ in columns)
            column_names = ", ".join(columns)

            connection.executemany(
                f"""
                INSERT INTO polizas_raw ({column_names})
                VALUES ({placeholders})
                """,
                [
                    (
                        batch_id,
                        row_number,
                        *(row[column] for column in POLICY_COLUMNS),
                    )
                    for row_number, row in enumerate(rows, start=2)
                ],
            )

    return {"rows_inserted": len(rows)}
