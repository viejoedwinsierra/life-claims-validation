-- P010: Incremental upgrade of an existing analytical database.
--
-- Adds the composite unique index required by the evaluation schema.
-- Preserves all ingested claim requests and their original identifiers.
-- Must be applied before migration 004 on legacy databases.
--
-- Idempotent: safe to execute more than once.

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_claims_analytics_raw_batch
ON reclamaciones_analytics(raw_id, batch_id);
