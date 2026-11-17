# ADR-002: SQLite persistence for claims

## Status

Accepted for the technical assessment.

## Context

The claims service must persist request identifiers,
business-event identities, processing states and Core results.
It must also support retries and duplicate detection.

## Decision

Use SQLite as the operational claims repository.
Keep the insurance Core as the authoritative policy source.
Initialize the schema from versioned SQL migration 001.
Persist the database in a Docker named volume.

## Implementation

- Repository: SQLiteClaimsRepository.
- Migration: datos/migrations/001_create_claims.sql.
- Container path: /app/data/claims.db.
- Docker volume: claims-data.
- Configuration: CLAIMS_DB_PATH.

Request-level idempotency uses id_solicitud and payload_hash.
Business-event identity uses business_event_key.
Database uniqueness constraints support atomic reservation.
BEGIN IMMEDIATE is used in the duplicate-rejection path.

## Alternatives

### PostgreSQL

Provides a possible path toward multi-instance deployment,
stronger operational tooling and higher write concurrency.
It would introduce additional infrastructure and operations.

### In-memory persistence

Simpler for isolated tests but unsuitable for restart
persistence and durable claim processing.

## Consequences

Positive:
- Simple local deployment.
- Durable storage through Docker volumes.
- Deterministic integration testing.
- No separate database server required.

Limitations:
- SQLite has a single-writer concurrency model.
- HTTP registration and SQLite updates are not atomic.
- Core timeouts may leave PENDING_CONFIRMATION records.
- Automatic reconciliation is not implemented.
- Multi-instance production scaling is not demonstrated.

## Future evolution

Evaluate PostgreSQL for production concurrency requirements.
Introduce reconciliation for uncertain Core outcomes.
Validate transaction boundaries and recovery procedures.

These improvements are proposals, not implemented features.
