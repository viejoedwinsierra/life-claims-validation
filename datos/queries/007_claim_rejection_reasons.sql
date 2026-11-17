-- P010: Rejection reasons KPI.
-- Source: transactional claim outcomes, not raw analytical requests.
-- Completed evaluations: REJECTED and REGISTERED.
-- A rejected claim can have multiple rejection reasons.

WITH completed AS (
    SELECT
        id_solicitud,
        estado,
        motivos_rechazo_json
    FROM reclamaciones
    WHERE estado IN ('REJECTED', 'REGISTERED')
),
totals AS (
    SELECT
        COUNT(*) AS evaluated_claims,
        COUNT(*) FILTER (
            WHERE estado = 'REJECTED'
        ) AS rejected_claims
    FROM completed
),
reason_occurrences AS (
    SELECT
        c.id_solicitud,
        j.value AS motivo
    FROM completed AS c
    JOIN json_each(c.motivos_rechazo_json) AS j
    WHERE c.estado = 'REJECTED'
      AND j.type = 'text'
),
reason_counts AS (
    SELECT
        motivo,
        COUNT(DISTINCT id_solicitud) AS solicitudes_con_motivo,
        COUNT(*) AS ocurrencias
    FROM reason_occurrences
    GROUP BY motivo
),
occurrence_total AS (
    SELECT COALESCE(SUM(ocurrencias), 0) AS total_ocurrencias
    FROM reason_counts
)
SELECT
    r.motivo,
    r.solicitudes_con_motivo,
    r.ocurrencias,
    t.evaluated_claims,
    t.rejected_claims,
    ROUND(
        100.0 * t.rejected_claims
        / NULLIF(t.evaluated_claims, 0),
        2
    ) AS porcentaje_rechazo_global,
    ROUND(
        100.0 * r.solicitudes_con_motivo
        / NULLIF(t.evaluated_claims, 0),
        2
    ) AS porcentaje_evaluadas_por_motivo,
    ROUND(
        100.0 * r.ocurrencias
        / NULLIF(o.total_ocurrencias, 0),
        2
    ) AS porcentaje_distribucion_motivos
FROM reason_counts AS r
CROSS JOIN totals AS t
CROSS JOIN occurrence_total AS o
ORDER BY r.motivo;
