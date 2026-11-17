# Containerization and local deployment

## Architecture

FastAPI runs inside Docker using Uvicorn.

- Internal API port: 8000
- Host API port: 8001
- SQLite database: /app/data/claims.db
- Persistent Docker volume: claims-data
- Core simulator: host.docker.internal:8081

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
