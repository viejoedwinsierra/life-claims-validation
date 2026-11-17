-- P007-07: Policy distribution by product and status.
-- Unit: RAW records, including duplicates.
-- Scope: one ingestion batch.

SELECT
    producto,
    estado,
    COUNT(*) AS total_registros
FROM polizas_raw
WHERE batch_id = :batch_id
GROUP BY
    producto,
    estado
ORDER BY
    producto,
    estado;
