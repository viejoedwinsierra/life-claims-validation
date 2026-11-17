"""Data quality metrics for an individual policy ingestion batch."""

import sqlite3
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from life_claims.infrastructure.policy_csv_ingestion import POLICY_COLUMNS

DATE_COLUMNS = (
    "fecha_nacimiento",
    "fecha_inicio_vigencia",
    "fecha_fin_vigencia",
    "fecha_cambio_estado",
    "fecha_actualizacion",
)


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date without silently truncating invalid values."""
    try:
        return date.fromisoformat(value.strip()) if value else None
    except ValueError:
        return None


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp without truncating its time."""
    try:
        return datetime.fromisoformat(value.strip()) if value else None
    except ValueError:
        return None


def _analyze_amounts(rows: list[dict]) -> dict[str, int]:
    """Count invalid, negative and zero insured amounts."""
    result = {
        "invalid_amounts": 0,
        "negative_amounts": 0,
        "zero_amounts": 0,
    }

    for row in rows:
        try:
            amount = Decimal(row["valor_asegurado"].strip())
        except (InvalidOperation, AttributeError):
            result["invalid_amounts"] += 1
            continue

        if not amount.is_finite():
            result["invalid_amounts"] += 1
        elif amount < 0:
            result["negative_amounts"] += 1
        elif amount == 0:
            result["zero_amounts"] += 1

    return result


def generate_policy_quality_report(
    database_path: str | Path,
    batch_id: int,
) -> dict:
    """Calculate quality metrics without modifying the RAW dataset."""
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        batch = connection.execute(
            "SELECT batch_id FROM ingestion_batches WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()

        if batch is None:
            raise ValueError("Unknown ingestion batch")

        records = connection.execute(
            """
            SELECT *
            FROM polizas_raw
            WHERE batch_id = ?
            ORDER BY source_row_number
            """,
            (batch_id,),
        ).fetchall()

    rows = [dict(record) for record in records]

    missing_values = {
        column: sum(value is None or not value.strip() for row in rows for value in [row[column]])
        for column in POLICY_COLUMNS
    }

    signatures = Counter(tuple(row[column] for column in POLICY_COLUMNS) for row in rows)

    exact_duplicates = sum(count - 1 for count in signatures.values() if count > 1)

    invalid_dates = {
        column: sum(
            (
                _parse_timestamp(row[column])
                if column == "fecha_actualizacion"
                else _parse_date(row[column])
            )
            is None
            for row in rows
        )
        for column in DATE_COLUMNS
    }

    inverted_ranges = 0

    for row in rows:
        start = _parse_date(row["fecha_inicio_vigencia"])
        end = _parse_date(row["fecha_fin_vigencia"])

        if start is not None and end is not None and start > end:
            inverted_ranges += 1

    result = {
        "batch_id": batch_id,
        "total_rows": len(rows),
        "distinct_policies": len({row["numero_poliza"] for row in rows}),
        "exact_duplicate_rows": exact_duplicates,
        "missing_values": missing_values,
        "invalid_dates": invalid_dates,
        "inverted_coverage_dates": inverted_ranges,
        "nonstandard_document_types": sum(row["tipo_documento_asegurado"] != "CC" for row in rows),
        "distributions": {
            column: dict(Counter(row[column] for row in rows))
            for column in ("producto", "estado", "canal_venta")
        },
    }

    result.update(_analyze_amounts(rows))

    return result
