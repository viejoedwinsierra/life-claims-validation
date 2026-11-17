"""Execute reproducible policy analytics queries."""

import re
import sqlite3
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

QUERY_PATH = Path(__file__).resolve().parents[3] / "datos" / "queries" / "002_insured_value.sql"


def _valid_amount(value: str | None) -> Decimal | None:
    """Accept positive amounts in conventional decimal notation."""
    if not isinstance(value, str):
        return None

    normalized = value.strip()

    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", normalized):
        return None

    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None

    if not amount.is_finite() or amount <= 0:
        return None

    return amount


def execute_insured_value_kpi(
    database_path: str | Path,
    batch_id: int,
) -> list[dict]:
    """Aggregate valid insured amounts by product and channel."""
    query = QUERY_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            query,
            {"batch_id": batch_id},
        ).fetchall()

    groups = defaultdict(
        lambda: {
            "total_registros": 0,
            "registros_validos": 0,
            "registros_excluidos": 0,
            "valor_asegurado_total": Decimal("0"),
        }
    )

    for producto, canal_venta, raw_amount in rows:
        group = groups[(producto, canal_venta)]
        group["total_registros"] += 1

        amount = _valid_amount(raw_amount)

        if amount is None:
            group["registros_excluidos"] += 1
        else:
            group["registros_validos"] += 1
            group["valor_asegurado_total"] += amount

    results = []

    for (producto, canal_venta), values in sorted(groups.items()):
        results.append(
            {
                "producto": producto,
                "canal_venta": canal_venta,
                "total_registros": values["total_registros"],
                "registros_validos": values["registros_validos"],
                "registros_excluidos": values["registros_excluidos"],
                "valor_asegurado_total": format(
                    values["valor_asegurado_total"],
                    ".2f",
                ),
            }
        )

    return results
