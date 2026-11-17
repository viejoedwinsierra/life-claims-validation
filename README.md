# Life Claims Validation

Modernization of a legacy life insurance claims validator.
Technical assessment: Andina Vida Seguros.

## Overview

Python service for validating and registering life insurance claims.

Main capabilities:
- Business validation rules R1-R8.
- REST API with FastAPI and OpenAPI.
- HTTP integration with the simulated Insurance Core.
- SQLite persistence and request idempotency.
- Business duplicate detection.
- CSV policy analytics and SQL KPIs.
- Automated tests and GitHub Actions CI.
- Docker deployment and architecture documentation.

## Architecture

The solution follows four application layers:

1. API: FastAPI endpoints and request schemas.
2. Application: claim processing orchestration.
3. Domain: business rules R1-R8 and event identity.
4. Infrastructure: SQLite repository and Core HTTP client.

Architecture documentation:

- [C4 L1 - Context](docs/arquitectura/C4-L1-contexto.md)
- [C4 L2 - Containers](docs/arquitectura/C4-L2-contenedores.md)
- [C4 L3 - Components](docs/arquitectura/C4-L3-componentes.md)
- [ADR-001 - Duplicates](docs/arquitectura/ADR-001-duplicidad-reclamaciones.md)
- [ADR-002 - SQLite](docs/arquitectura/ADR-002-persistencia-sqlite.md)
- [ADR-003 - Core integration](docs/arquitectura/ADR-003-integracion-core.md)

## Local installation

Requirements: Python 3.12 and the external Insurance Core.

Install dependencies: pip install -e .

Configure environment variables:
- CLAIMS_DB_PATH=/tmp/life-claims.db
- CORE_BASE_URL=http://localhost:8081

Initialize the database:
python -m life_claims.infrastructure.init_claims_db

Start the API:
uvicorn life_claims.api.main:app --host 127.0.0.1 --port 8001

## Docker deployment

Build and start: docker compose up --build -d

Local API: http://127.0.0.1:8001
Health: http://127.0.0.1:8001/health
OpenAPI: http://127.0.0.1:8001/docs

Configuration:
- Container port: 8000.
- Published localhost port: 8001.
- SQLite database: /app/data/claims.db.
- Persistent Docker volume: claims-data.
- External Core URL: CORE_BASE_URL.

The simulated Core must run separately.

## REST API

GET /health - Check service health.
POST /reclamaciones - Submit an insurance claim.
GET /reclamaciones/{id_solicitud} - Retrieve a claim.

Possible claim states:
- REGISTERED: successfully registered in the Core.
- REJECTED: business validation failed.
- PENDING_CONFIRMATION: Core registration timed out.
- IN_PROGRESS: an equivalent event is being processed.

HTTP responses include 200, 201, 202, 404, 409 and 422.
The API contract is exposed at /openapi.json.

## Automated verification

Run unit and integration tests: pytest -q
Run static analysis: ruff check .
Validate Docker configuration: docker compose config -q

GitHub Actions runs automated quality checks.
The CI workflow also includes a Docker image build.

## Policy data analytics

The project provides Python modules for:
- CSV policy ingestion into SQLite.
- Data quality analysis.
- Policy validity analysis.
- SQL KPI generation.

Analytics data is separate from operational Core validation.

Documentation:
[Data ingestion and quality](docs/DATA_INGESTION_AND_QUALITY.md)

## Engineering evidence

- [AI collaboration log](AI_LOG.md)
- [Containerization](docs/CONTAINERIZATION.md)
- Versioned SQL migrations in datos/migrations/.
- Automated tests in tests/.
- Git commit history and GitHub Actions workflows.

## Known limitations

- SQLite is used instead of PostgreSQL.
- No distributed transaction exists with the Core.
- Core timeouts may produce PENDING_CONFIRMATION.
- Automatic Core reconciliation is not implemented.
- Non-timeout Core failures need additional recovery handling.
- Production scalability and high availability are not demonstrated.

## Confidentiality

The assessment kit and simulated Core distribution are
excluded from Git and the application Docker image.
