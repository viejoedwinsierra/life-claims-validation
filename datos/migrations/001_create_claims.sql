-- Migration 001: transactional persistence for insurance claims.

CREATE TABLE IF NOT EXISTS reclamaciones (
    id_solicitud TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    business_event_key TEXT,
    numero_poliza TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'RECEIVED'
        CHECK (
            estado IN (
                'RECEIVED',
                'REJECTED',
                'REGISTERED',
                'PENDING_CONFIRMATION',
                'TECHNICAL_ERROR'
            )
        ),
    motivos_rechazo_json TEXT NOT NULL DEFAULT '[]',
    numero_siniestro TEXT,
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reclamaciones_poliza
    ON reclamaciones (numero_poliza);

CREATE INDEX IF NOT EXISTS idx_reclamaciones_estado
    ON reclamaciones (estado);


-- Only active or confirmed claims retain the business-event reservation.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reclamaciones_business_event
ON reclamaciones (business_event_key)
WHERE business_event_key IS NOT NULL
  AND estado IN ('RECEIVED', 'REGISTERED', 'PENDING_CONFIRMATION',
                 'TECHNICAL_ERROR');
