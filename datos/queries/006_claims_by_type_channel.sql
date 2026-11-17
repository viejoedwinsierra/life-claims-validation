-- P010: Claim requests by type and channel.
-- Counts received requests, not approved or rejected claims.
-- Percentages use the total number of imported requests.

WITH grouped AS (
    SELECT
        tipo_reclamacion,
        canal,
        COUNT(*) AS cantidad
    FROM reclamaciones_analytics
    GROUP BY tipo_reclamacion, canal
),
total AS (
    SELECT COUNT(*) AS total_reclamaciones
    FROM reclamaciones_analytics
)
SELECT
    grouped.tipo_reclamacion,
    grouped.canal,
    grouped.cantidad,
    total.total_reclamaciones,
    ROUND(
        100.0 * grouped.cantidad
        / NULLIF(total.total_reclamaciones, 0),
        2
    ) AS porcentaje_total
FROM grouped
CROSS JOIN total
ORDER BY
    grouped.tipo_reclamacion,
    grouped.canal;
