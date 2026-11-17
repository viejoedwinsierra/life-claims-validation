-- P007-10: Completeness by product.
-- Unit: RAW records, including duplicates.
-- Scope: one ingestion batch.
-- Missing: NULL, empty string or whitespace.

SELECT
    producto,
    COUNT(*) AS total_registros,
    SUM(
        CASE
            WHEN producto IS NULL OR TRIM(producto) = ''
            THEN 1 ELSE 0
        END
    ) AS producto_faltante,
    SUM(
        CASE
            WHEN nombre_asegurado IS NULL
              OR TRIM(nombre_asegurado) = ''
            THEN 1 ELSE 0
        END
    ) AS nombre_faltante,
    SUM(
        CASE
            WHEN amparos IS NULL OR TRIM(amparos) = ''
            THEN 1 ELSE 0
        END
    ) AS amparos_faltantes
FROM polizas_raw
WHERE batch_id = :batch_id
GROUP BY producto
ORDER BY producto;
