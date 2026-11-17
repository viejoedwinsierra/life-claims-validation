"""Integration tests for policy data quality reporting."""

import csv
import sqlite3

import pytest

from life_claims.infrastructure.policy_csv_ingestion import (
    POLICY_COLUMNS,
    ingest_policy_csv,
)
from life_claims.infrastructure.policy_quality_report import (
    generate_policy_quality_report,
)


def test_quality_report_is_scoped_to_one_batch(tmp_path):
    """Quality metrics must not combine separate ingestion batches."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    row = dict.fromkeys(POLICY_COLUMNS, "")
    row.update(
        numero_poliza="POL-001",
        producto="VIDA_INDIVIDUAL",
        tipo_documento_asegurado="C.C.",
        nombre_asegurado="",
        fecha_inicio_vigencia="INVALID",
        fecha_fin_vigencia="2025-01-01",
        valor_asegurado="-100",
        amparos="",
    )

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerows([row, row])

    ingest_policy_csv(csv_path, database_path)

    with sqlite3.connect(database_path) as connection:
        batch_id = connection.execute("SELECT batch_id FROM ingestion_batches").fetchone()[0]

    report = generate_policy_quality_report(database_path, batch_id)

    assert report["batch_id"] == batch_id
    assert report["total_rows"] == 2
    assert report["distinct_policies"] == 1
    assert report["exact_duplicate_rows"] == 1

    assert report["missing_values"]["nombre_asegurado"] == 2
    assert report["missing_values"]["amparos"] == 2

    assert report["invalid_dates"]["fecha_inicio_vigencia"] == 2
    assert report["invalid_dates"]["fecha_fin_vigencia"] == 0

    assert report["invalid_amounts"] == 0
    assert report["negative_amounts"] == 2
    assert report["zero_amounts"] == 0

    assert report["nonstandard_document_types"] == 2


def test_quality_report_rejects_unknown_batch(tmp_path):
    """Unknown batches must fail explicitly."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    row = dict.fromkeys(POLICY_COLUMNS, "")
    row["numero_poliza"] = "POL-001"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    ingest_policy_csv(csv_path, database_path)

    with pytest.raises(ValueError, match="Unknown ingestion batch"):
        generate_policy_quality_report(database_path, 999999)


def test_quality_report_accepts_iso_update_timestamps(tmp_path):
    """Valid ISO timestamps must not count as invalid updates."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    row = dict.fromkeys(POLICY_COLUMNS, "")
    row.update(
        numero_poliza="POL-001",
        tipo_documento_asegurado="CC",
        fecha_actualizacion="2025-10-15T14:30:00",
    )

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    ingest_policy_csv(csv_path, database_path)

    report = generate_policy_quality_report(database_path, 1)

    assert report["invalid_dates"]["fecha_actualizacion"] == 0


def test_quality_report_rejects_invalid_update_timestamps(tmp_path):
    """Malformed timestamps must be reported as invalid."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    row = dict.fromkeys(POLICY_COLUMNS, "")
    row.update(
        numero_poliza="POL-002",
        tipo_documento_asegurado="CC",
        fecha_actualizacion="2025-99-99T25:61:00",
    )

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    ingest_policy_csv(csv_path, database_path)

    report = generate_policy_quality_report(database_path, 1)

    assert report["invalid_dates"]["fecha_actualizacion"] == 1
