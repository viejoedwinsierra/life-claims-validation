-- P007-09: Policy coverage date quality.
-- Requires SQLite UDF is_valid_iso_date(value).
-- RAW records, including duplicates.

WITH validated AS (
    SELECT
        producto,
        estado,
        fecha_inicio_vigencia,
        fecha_fin_vigencia,
        is_valid_iso_date(fecha_inicio_vigencia) AS start_valid,
        is_valid_iso_date(fecha_fin_vigencia) AS end_valid
    FROM polizas_raw
    WHERE batch_id = :batch_id
)
SELECT
    producto,
    estado,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN start_valid = 0 THEN 1 ELSE 0 END)
        AS fechas_inicio_invalidas,
    SUM(CASE WHEN end_valid = 0 THEN 1 ELSE 0 END)
        AS fechas_fin_invalidas,
    SUM(
        CASE
            WHEN start_valid = 1
             AND end_valid = 1
             AND fecha_inicio_vigencia > fecha_fin_vigencia
            THEN 1
            ELSE 0
        END
    ) AS vigencias_invertidas
FROM validated
GROUP BY producto, estado
ORDER BY producto, estado;
