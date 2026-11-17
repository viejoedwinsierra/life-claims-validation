"""Integration tests for policy analytics SQL."""

import csv
import sqlite3
from pathlib import Path

from life_claims.infrastructure.policy_csv_ingestion import (
    POLICY_COLUMNS,
    ingest_policy_csv,
)

QUERY_PATH = (
    Path(__file__).resolve().parents[2] / "datos" / "queries" / "001_policy_distribution.sql"
)


def test_policy_distribution_query(tmp_path):
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    rows = []

    for policy, product, status in [
        ("POL-001", "VIDA_INDIVIDUAL", "VIGENTE"),
        ("POL-002", "VIDA_INDIVIDUAL", "TERMINADA"),
        ("POL-003", "ACCIDENTES_PERSONALES", "VIGENTE"),
    ]:
        row = dict.fromkeys(POLICY_COLUMNS, "")
        row.update(
            numero_poliza=policy,
            producto=product,
            estado=status,
        )
        rows.append(row)

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    ingest_policy_csv(csv_path, database_path)

    query = QUERY_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        results = connection.execute(query, {"batch_id": 1}).fetchall()

    assert sorted(results) == sorted(
        [
            ("ACCIDENTES_PERSONALES", "VIGENTE", 1),
            ("VIDA_INDIVIDUAL", "TERMINADA", 1),
            ("VIDA_INDIVIDUAL", "VIGENTE", 1),
        ]
    )

    assert sum(row[2] for row in results) == 3


def test_insured_value_query_excludes_invalid_amounts(tmp_path):
    """Financial KPI must exclude invalid, zero and negative amounts."""
    from life_claims.infrastructure.policy_kpi_runner import (
        execute_insured_value_kpi,
    )

    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    amounts = ["100.50", "200", "-50", "0", "INVALID", "1e999"]

    rows = []
    for index, amount in enumerate(amounts, start=1):
        row = dict.fromkeys(POLICY_COLUMNS, "")
        row.update(
            numero_poliza=f"POL-{index:03d}",
            producto="VIDA_INDIVIDUAL",
            canal_venta="DIRECTO",
            valor_asegurado=amount,
        )
        rows.append(row)

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    ingest_policy_csv(csv_path, database_path)

    results = execute_insured_value_kpi(database_path, batch_id=1)

    assert len(results) == 1

    result = results[0]

    assert result["producto"] == "VIDA_INDIVIDUAL"
    assert result["canal_venta"] == "DIRECTO"
    assert result["total_registros"] == 6
    assert result["registros_validos"] == 2
    assert result["registros_excluidos"] == 4
    assert result["valor_asegurado_total"] == "300.50"


def test_policy_validity_query(tmp_path):
    """Detect invalid and inverted coverage dates by product and status."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    cases = [
        ("POL-001", "2025-01-01", "2025-12-31"),
        ("POL-002", "INVALID", "2025-12-31"),
        ("POL-003", "2025-01-01", "INVALID"),
        ("POL-004", "2025-12-31", "2025-01-01"),
    ]

    rows = []

    for policy, start, end in cases:
        row = dict.fromkeys(POLICY_COLUMNS, "")
        row.update(
            numero_poliza=policy,
            producto="VIDA_INDIVIDUAL",
            estado="VIGENTE",
            fecha_inicio_vigencia=start,
            fecha_fin_vigencia=end,
        )
        rows.append(row)

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    ingest_policy_csv(csv_path, database_path)

    query_path = (
        Path(__file__).resolve().parents[2] / "datos" / "queries" / "003_policy_validity.sql"
    )

    query = query_path.read_text(encoding="utf-8")

    from life_claims.infrastructure.policy_validity_runner import (
        is_valid_iso_date,
    )

    with sqlite3.connect(database_path) as connection:
        connection.create_function(
            "is_valid_iso_date",
            1,
            is_valid_iso_date,
        )
        result = connection.execute(query, {"batch_id": 1}).fetchone()

    assert result == (
        "VIDA_INDIVIDUAL",
        "VIGENTE",
        4,
        1,
        1,
        1,
    )


def test_policy_completeness_query(tmp_path):
    """Count missing mandatory fields without deduplicating RAW records."""
    csv_path = tmp_path / "polizas.csv"
    database_path = tmp_path / "analytics.sqlite3"

    cases = [
        ("POL-001", "VIDA_INDIVIDUAL", "Ana", "VIDA"),
        ("POL-002", "VIDA_INDIVIDUAL", "", "VIDA"),
        ("POL-003", "VIDA_INDIVIDUAL", "Luis", ""),
        ("POL-004", "", "Maria", "VIDA"),
    ]

    rows = []

    for policy, product, name, coverage in cases:
        row = dict.fromkeys(POLICY_COLUMNS, "")
        row.update(
            numero_poliza=policy,
            producto=product,
            nombre_asegurado=name,
            amparos=coverage,
        )
        rows.append(row)

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    ingest_policy_csv(csv_path, database_path)

    query_path = (
        Path(__file__).resolve().parents[2] / "datos" / "queries" / "004_policy_completeness.sql"
    )

    query = query_path.read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        results = connection.execute(query, {"batch_id": 1}).fetchall()

    assert results == [
        ("", 1, 1, 0, 0),
        ("VIDA_INDIVIDUAL", 3, 0, 1, 1),
    ]


def test_policy_validity_rejects_impossible_calendar_dates():
    """Validate calendar dates, including leap years."""
    from life_claims.infrastructure.policy_validity_runner import (
        is_valid_iso_date,
    )

    cases = [
        ("2025-02-28", 1),
        ("2025-02-30", 0),
        ("2024-02-29", 1),
        ("2025-02-29", 0),
        ("2025-13-01", 0),
        ("", 0),
    ]

    for value, expected in cases:
        assert is_valid_iso_date(value) == expected
