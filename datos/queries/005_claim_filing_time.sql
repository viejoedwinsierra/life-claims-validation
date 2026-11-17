-- P010: Claim filing time KPI.
-- Calendar days between loss date and filing date.
-- Negative intervals are excluded from the average.
-- Late claims (>730 days) remain in the average.

WITH tiempos AS (
    SELECT
        raw_id,
        CAST(
            julianday(date(fecha_radicacion))
            - julianday(date(fecha_siniestro))
            AS INTEGER
        ) AS dias
    FROM reclamaciones_analytics
)
SELECT
    COUNT(*) AS total_reclamaciones,
    SUM(CASE WHEN dias < 0 THEN 1 ELSE 0 END)
        AS fechas_inconsistentes,
    SUM(CASE WHEN dias BETWEEN 0 AND 730 THEN 1 ELSE 0 END)
        AS dentro_plazo,
    SUM(CASE WHEN dias > 730 THEN 1 ELSE 0 END)
        AS radicaciones_tardias,
    COUNT(CASE WHEN dias >= 0 THEN 1 END)
        AS reclamaciones_promedio,
    ROUND(AVG(CASE WHEN dias >= 0 THEN dias END), 2)
        AS promedio_dias
FROM tiempos;
