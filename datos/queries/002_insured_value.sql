-- P007-08: Insured value records by product and sales channel.
-- Unit: RAW records, including duplicates.
-- Scope: one ingestion batch.
-- Monetary validation and aggregation use Python Decimal.

SELECT
    producto,
    canal_venta,
    valor_asegurado
FROM polizas_raw
WHERE batch_id = :batch_id
ORDER BY
    producto,
    canal_venta,
    raw_id;
