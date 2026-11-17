-- P010: Add optional Core snapshot provenance to existing evaluations.
-- Apply only to databases that already have migration 004 installed.
-- A NULL value means no verified Core snapshot was provided.

ALTER TABLE claims_evaluation_runs
ADD COLUMN core_snapshot_sha256 TEXT
CHECK (
    core_snapshot_sha256 IS NULL
    OR (
        length(core_snapshot_sha256) = 64
        AND core_snapshot_sha256 NOT GLOB '*[^0-9a-f]*'
    )
);
