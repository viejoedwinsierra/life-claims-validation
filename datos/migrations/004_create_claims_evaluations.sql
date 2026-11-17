-- P010: Persist read-only claim evaluation results.
-- Analytical tables only. No Core registrations.

CREATE TABLE IF NOT EXISTS claims_evaluation_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    evaluation_date TEXT NOT NULL,
    evaluation_method TEXT NOT NULL
        CHECK (evaluation_method IN ('READ_ONLY')),
    r8_source TEXT NOT NULL,
    core_snapshot_sha256 TEXT
        CHECK (
            core_snapshot_sha256 IS NULL
            OR (
                length(core_snapshot_sha256) = 64
                AND core_snapshot_sha256 NOT GLOB '*[^0-9a-f]*'
            )
        ),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES claims_ingestion_batches(batch_id),

    UNIQUE (run_id, batch_id)
);

CREATE TABLE IF NOT EXISTS claims_evaluation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    raw_id INTEGER NOT NULL,
    estado TEXT NOT NULL
        CHECK (
            estado IN (
                'VALID',
                'REJECTED',
                'TECHNICAL_ERROR'
            )
        ),
    motivos_rechazo_json TEXT NOT NULL DEFAULT '[]'
        CHECK (
            json_valid(motivos_rechazo_json)
            AND json_type(motivos_rechazo_json) = 'array'
        ),
    error_tecnico TEXT,
    CHECK (
        (
            estado = 'VALID'
            AND json_array_length(motivos_rechazo_json) = 0
            AND error_tecnico IS NULL
        )
        OR (
            estado = 'REJECTED'
            AND json_array_length(motivos_rechazo_json) > 0
            AND error_tecnico IS NULL
        )
        OR (
            estado = 'TECHNICAL_ERROR'
            AND json_array_length(motivos_rechazo_json) = 0
            AND error_tecnico IS NOT NULL
            AND length(trim(error_tecnico)) > 0
        )
    ),

    FOREIGN KEY (run_id, batch_id)
        REFERENCES claims_evaluation_runs(run_id, batch_id),

    FOREIGN KEY (raw_id, batch_id)
        REFERENCES reclamaciones_analytics(raw_id, batch_id),

    UNIQUE (run_id, raw_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_evaluation_results_estado
ON claims_evaluation_results(run_id, estado);

-- Validate every rejection reason, not only the first element.
-- Triggers complement the CHECK constraints on result consistency.

CREATE TRIGGER IF NOT EXISTS trg_claims_evaluation_reasons_insert
BEFORE INSERT ON claims_evaluation_results
WHEN json_valid(NEW.motivos_rechazo_json) = 1
BEGIN
    SELECT RAISE(ABORT, 'Invalid rejection reason')
    WHERE EXISTS (
        SELECT 1
        FROM json_each(NEW.motivos_rechazo_json)
        WHERE type <> 'text'
           OR value NOT IN (
               'R1', 'R2', 'R3', 'R4',
               'R5', 'R6', 'R7', 'R8'
           )
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_claims_evaluation_reasons_update
BEFORE UPDATE OF motivos_rechazo_json
ON claims_evaluation_results
WHEN json_valid(NEW.motivos_rechazo_json) = 1
BEGIN
    SELECT RAISE(ABORT, 'Invalid rejection reason')
    WHERE EXISTS (
        SELECT 1
        FROM json_each(NEW.motivos_rechazo_json)
        WHERE type <> 'text'
           OR value NOT IN (
               'R1', 'R2', 'R3', 'R4',
               'R5', 'R6', 'R7', 'R8'
           )
    );
END;
