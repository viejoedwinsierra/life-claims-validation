"""Orchestrate read-only claim evaluation and persistence."""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from life_claims.application.claims_batch_evaluator import evaluate_batch
from life_claims.infrastructure.claims_evaluation_repository import (
    ClaimsEvaluationRepository,
)


def evaluate_and_save_batch(
    *,
    database: str | Path,
    batch_id: int,
    core: Any,
    today: date,
    r8_source: str,
    repository: Any | None = None,
    core_snapshot_sha256: str | None = None,
) -> int:
    """Evaluate a complete ingestion batch without Core registration."""
    database = Path(database)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM reclamaciones_analytics
            WHERE batch_id = ?
            ORDER BY source_row_number
            """,
            (batch_id,),
        ).fetchall()

    if not rows:
        raise ValueError("Batch has no claims")

    claims = [json.loads(payload) for (payload,) in rows]

    results = evaluate_batch(
        claims=claims,
        core=core,
        today=today,
        repository=repository,
    )

    evaluation_repository = ClaimsEvaluationRepository(database)

    return evaluation_repository.save_run(
        batch_id=batch_id,
        evaluation_date=today.isoformat(),
        r8_source=r8_source,
        results=results,
        core_snapshot_sha256=core_snapshot_sha256,
    )
