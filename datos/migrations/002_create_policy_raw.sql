-- P007: Lossless CSV ingestion for policy analytics.
-- This database is not the authoritative policy core.

CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename TEXT NOT NULL,
    source_sha256 TEXT NOT NULL UNIQUE,
    rows_inserted INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polizas_raw (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    source_row_number INTEGER NOT NULL,

    numero_poliza TEXT,
    producto TEXT,
    tipo_documento_asegurado TEXT,
    numero_documento_asegurado TEXT,
    nombre_asegurado TEXT,
    fecha_nacimiento TEXT,
    fecha_inicio_vigencia TEXT,
    fecha_fin_vigencia TEXT,
    estado TEXT,
    fecha_cambio_estado TEXT,
    amparos TEXT,
    valor_asegurado TEXT,
    canal_venta TEXT,
    ciudad TEXT,
    fecha_actualizacion TEXT,

    FOREIGN KEY (batch_id)
        REFERENCES ingestion_batches(batch_id),

    UNIQUE (batch_id, source_row_number)
);

CREATE INDEX IF NOT EXISTS idx_polizas_raw_numero
ON polizas_raw(numero_poliza);
