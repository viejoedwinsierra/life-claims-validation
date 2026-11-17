-- P010: Analytical ingestion of claim requests.
-- No Core operations or claim registrations occur here.

CREATE TABLE IF NOT EXISTS claims_ingestion_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename TEXT NOT NULL,
    source_sha256 TEXT NOT NULL UNIQUE,
    rows_inserted INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reclamaciones_analytics (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    source_row_number INTEGER NOT NULL,
    id_solicitud TEXT,
    numero_poliza TEXT,
    canal TEXT,
    tipo_reclamacion TEXT,
    fecha_siniestro TEXT,
    fecha_radicacion TEXT,
    payload_json TEXT NOT NULL,

    FOREIGN KEY (batch_id)
        REFERENCES claims_ingestion_batches(batch_id),

    UNIQUE (batch_id, source_row_number),
    UNIQUE (raw_id, batch_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_analytics_tipo_canal
ON reclamaciones_analytics(tipo_reclamacion, canal);

CREATE INDEX IF NOT EXISTS idx_claims_analytics_solicitud
ON reclamaciones_analytics(id_solicitud);
