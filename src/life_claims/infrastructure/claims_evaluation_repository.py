"""SQLite persistence for read-only batch evaluations."""

import json
import sqlite3
from pathlib import Path


class ClaimsEvaluationRepository:
    """Persist evaluations without modifying claims or calling Core."""

    def __init__(self, database: str | Path):
        self.database = Path(database)

    def save_run(
        self,
        *,
        batch_id: int,
        evaluation_date: str,
        r8_source: str,
        results: list[dict],
        core_snapshot_sha256: str | None = None,
    ) -> int:
        """Atomically persist one complete evaluation of an ingestion batch."""
        with sqlite3.connect(self.database) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            claims = connection.execute(
                """
                SELECT raw_id, id_solicitud
                FROM reclamaciones_analytics
                WHERE batch_id = ?
                ORDER BY source_row_number
                """,
                (batch_id,),
            ).fetchall()

            if not claims:
                raise ValueError("Batch has no claims")

            identifiers = [identifier for _, identifier in claims]

            if any(identifier is None for identifier in identifiers):
                raise ValueError("Claim identifier cannot be null")

            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Duplicate claim identifiers in batch")

            result_ids = [result["id_solicitud"] for result in results]

            if (
                len(results) != len(claims)
                or len(set(result_ids)) != len(result_ids)
                or set(result_ids) != set(identifiers)
            ):
                raise ValueError(
                    "Evaluation results must match all batch claims exactly"
                )

            raw_ids = {
                identifier: raw_id
                for raw_id, identifier in claims
            }

            run_id = connection.execute(
                """
                INSERT INTO claims_evaluation_runs (
                    batch_id,
                    evaluation_date,
                    evaluation_method,
                    r8_source,
                    core_snapshot_sha256
                )
                VALUES (?, ?, 'READ_ONLY', ?, ?)
                """,
                (
                    batch_id,
                    evaluation_date,
                    r8_source,
                    core_snapshot_sha256,
                ),
            ).lastrowid

            for result in results:
                connection.execute(
                    """
                    INSERT INTO claims_evaluation_results (
                        run_id,
                        batch_id,
                        raw_id,
                        estado,
                        motivos_rechazo_json,
                        error_tecnico
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        batch_id,
                        raw_ids[result["id_solicitud"]],
                        result["estado"],
                        json.dumps(
                            result.get("motivos_rechazo", []),
                            ensure_ascii=False,
                        ),
                        result.get("error_tecnico"),
                    ),
                )

            return run_id
