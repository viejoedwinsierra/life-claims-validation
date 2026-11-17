"""Integration tests for lossless policy CSV ingestion."""

import csv
import sqlite3

from life_claims.infrastructure.policy_csv_ingestion import ingest_policy_csv


def test_ingestion_preserves_all_rows_and_is_idempotent(tmp_path):
    """Reprocessing the same file must not duplicate RAW rows."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    columns = [
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
    ]

    first = dict.fromkeys(columns, "")
    first["numero_poliza"] = "POL-001"
    first["tipo_documento_asegurado"] = "C.C."
    first["valor_asegurado"] = "INVALID"

    second = first.copy()
    second["numero_poliza"] = "POL-002"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows([first, first, second])

    first_result = ingest_policy_csv(csv_path, database_path)
    second_result = ingest_policy_csv(csv_path, database_path)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                source_row_number,
                numero_poliza,
                tipo_documento_asegurado,
                valor_asegurado
            FROM polizas_raw
            ORDER BY source_row_number
            """
        ).fetchall()

        batch_count = connection.execute("SELECT COUNT(*) FROM ingestion_batches").fetchone()[0]

    assert first_result["rows_inserted"] == 3
    assert second_result["rows_inserted"] == 0
    assert batch_count == 1

    assert rows == [
        (2, "POL-001", "C.C.", "INVALID"),
        (3, "POL-001", "C.C.", "INVALID"),
        (4, "POL-002", "C.C.", "INVALID"),
    ]


def test_ingestion_rejects_missing_file(tmp_path):
    """Missing source files must fail explicitly."""
    csv_path = tmp_path / "missing.csv"
    database_path = tmp_path / "analytics.sqlite3"

    try:
        ingest_policy_csv(csv_path, database_path)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_ingestion_rejects_unexpected_columns(tmp_path):
    """Invalid headers must not create an ingestion batch."""
    csv_path = tmp_path / "invalid.csv"
    database_path = tmp_path / "analytics.sqlite3"

    csv_path.write_text(
        "numero_poliza,columna_incorrecta\nPOL-001,X\n",
        encoding="utf-8",
    )

    try:
        ingest_policy_csv(csv_path, database_path)
    except ValueError as exc:
        assert "Unexpected policy CSV columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert not database_path.exists()


def test_changed_csv_creates_a_new_batch(tmp_path):
    """A modified source must be ingested as a separate batch."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    from life_claims.infrastructure.policy_csv_ingestion import POLICY_COLUMNS

    row = dict.fromkeys(POLICY_COLUMNS, "")
    row["numero_poliza"] = "POL-001"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    first = ingest_policy_csv(csv_path, database_path)

    row["numero_poliza"] = "POL-002"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)

    second = ingest_policy_csv(csv_path, database_path)

    with sqlite3.connect(database_path) as connection:
        batches = connection.execute("SELECT COUNT(*) FROM ingestion_batches").fetchone()[0]

        rows = connection.execute("SELECT COUNT(*) FROM polizas_raw").fetchone()[0]

    assert first["rows_inserted"] == 1
    assert second["rows_inserted"] == 1
    assert batches == 2
    assert rows == 2
