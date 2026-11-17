# Containerization and local deployment

## Architecture

FastAPI runs inside Docker using Uvicorn.

- Internal API port: 8000
- Host API port: 8001
- SQLite database: /app/data/claims.db
- Persistent Docker volume: claims-data
- Core simulator: core-simulado:8081

The confidential Core simulator is excluded from the image.

## Start

Run: docker compose up -d --build
Check: docker compose ps
Health: curl http://localhost:8001/health

## Database initialization

The container executes migration 001 before starting Uvicorn.
Migration: datos/migrations/001_create_claims.sql

## Persistence

Restart: docker compose restart claims-api
The named volume preserves SQLite data.
Avoid docker compose down -v when data must be preserved.

## E2E evidence - 2026-11-17

- Policy: AV-VI-0100004
- POST /reclamaciones: HTTP 201 REGISTERED
- Claim: SIN-20261117-CE3695C7
- GET /reclamaciones/E2E-P008-001: HTTP 200
- Repeated POST: same claim number
- SQLite: one record
- Restart: claim persisted
- Docker health: healthy
- Pytest: 131 passed
- Ruff: all checks passed

Core failure injection may produce transient failures.

## P011 - Docker Compose and structured logging

Docker Compose starts two services:

- claims-api: FastAPI with persistent SQLite storage.
- core-simulado: original assessment Core on the internal Docker network.

The API connects to http://core-simulado:8081.

The confidential Core files must be available locally:

- kit_prueba_tecnica/core_simulado/core_simulado.py
- kit_prueba_tecnica/core_simulado/polizas_core.json

The Core directory is excluded from Git and mounted read-only.
Evaluators must use their authorized copy of the assessment kit.

### Structured HTTP logging

The API generates JSON events with:

- timestamp
- level
- event
- request_id
- method
- path
- status_code
- duration_ms

The X-Request-ID response header provides the correlation identifier.
The middleware does not log request bodies.

### Verification

- Docker Compose: PASS
- API health: HTTP 200
- Core health from API: HTTP 200
- JSON logging: HTTP 200 and HTTP 404 verified
- Pytest: 160 passed
- Ruff: PASS
