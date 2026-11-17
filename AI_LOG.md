# AI-Assisted Engineering Log

## Technical Assessment - Andina Vida Seguros

Project: Life Claims Validation
Dates: November 16-17, 2026
AI assistant: ChatGPT
Human engineer: Edwin Gustavo Sierra Poveda

## 1. Purpose and methodology

This log documents the complete engineering collaboration
between the candidate and ChatGPT during the assessment.

The workflow combined:
- Requirements analysis and technical decomposition.
- Incremental test-driven development (TDD).
- Architecture and implementation decisions.
- Local execution and troubleshooting.
- Automated verification and Git traceability.

ChatGPT suggested implementations, tests and diagnostics.
The engineer reviewed, executed and validated the work.

## 2. P001 - Repository and legacy baseline

The project was initialized with a legacy validation baseline.
The confidential assessment kit was excluded from version control.
A structured Python project was established.
A develop branch and feature-based workflow were adopted.

Engineering decisions:
- Preserve confidential assessment materials locally.
- Separate production code from tests and documentation.
- Use small commits and feature branches.

## 3. P002 - Continuous integration foundation

A GitHub Actions pipeline was introduced.
Python 3.12 was selected for automated execution.
Ruff was configured for static quality checks.
Pytest was integrated into the pipeline.

The objective was to detect regressions early and
maintain a reproducible development process.

## 4. P003 - Claims validation business rules

Business rules R1-R8 were implemented incrementally.
Date validation was developed with boundary-focused tests.
Policy rules and coverage checks were added.
Duplicate detection was scoped to policy identity.
Core contracts were normalized.
Insured identity validation was strengthened.

TDD evidence:
- Tests for date rules preceded implementation.
- Tests for policy rules preceded implementation.
- Duplicate-detection behavior was refined.
- The domain validation rules were integrated.

Architecture evidence:
docs/arquitectura/ADR-001-duplicidad-reclamaciones.md

## 5. P004 - Insurance Core HTTP integration

An HTTP client was implemented for the simulated Core.
The client separated infrastructure concerns from domain rules.
Core response normalization supported validation.
Filing datetime compatibility was subsequently corrected.

Engineering considerations:
- The Core is authoritative for operational policy data.
- Network integration must remain testable independently.
- The confidential simulator is not committed.

## 6. P005 - Application service and persistence

An application service orchestrated claim processing.
SQLite persistence was implemented.
The design separated domain, application and infrastructure.
Idempotency and stored claim retrieval were tested.

The service coordinated validation, Core communication
and persistence through explicit dependencies.

## 7. P006 - FastAPI and OpenAPI

The HTTP interface was implemented using FastAPI.
POST /reclamaciones registers a claim.
GET /reclamaciones/{id_solicitud} retrieves a claim.
GET /health exposes application health.
OpenAPI contract tests were introduced.

Integration tests covered HTTP responses and SQLite behavior.
The feature was merged into develop.

## 8. P007 - Data ingestion and analytics

CSV ingestion was implemented using SQLite.
Quality checks and reporting were added.
SQL queries supported policy KPIs.

Observed dataset results:
- Input rows: 4950.
- Distinct policies: 4850.
- Exact duplicate rows: 60.

The CSV supports analytics and quality analysis.
It does not replace the Core as the operational source.

Documentation:
docs/DATA_INGESTION_AND_QUALITY.md

## 9. P008 - Docker and continuous delivery checks

A Dockerfile and Docker Compose configuration were created.
The API runs on container port 8000 and host port 8001.
SQLite uses a persistent named Docker volume.
The Core simulator remains external on host port 8081.

An initialization module applies SQL migration 001.
The migration was tested for repeated execution.

Troubleshooting:
- Docker build context initially excluded the SQL migration.
- The .dockerignore rules were corrected.
- Early HTTP checks occurred before container readiness.
- Health was confirmed after successful startup.
- A terminal buffer issue was resolved when writing docs.

## 10. End-to-end validation

Policy: AV-VI-0100004.
Coverage: MUERTE.
Loss date: 2026-10-18.
Request ID: E2E-P008-001.

Observed results:
- POST /reclamaciones: HTTP 201, REGISTERED.
- Claim number: SIN-20261117-CE3695C7.
- GET /reclamaciones/E2E-P008-001: HTTP 200.
- Repeated POST returned the same claim number.
- SQLite retained one record for the request.
- The record survived a container restart.

## 11. Final local quality verification

Pytest: 131 passed, 1 deprecation warning.
Ruff: all checks passed.
Docker Compose configuration: valid.
Docker image: built successfully.
GitHub-hosted Docker CI: not yet verified.

## 12. AI contributions and human accountability

ChatGPT assisted with architecture, test design,
implementation proposals, troubleshooting and documentation.

The engineer retained responsibility for:
- Reviewing code and accepting design decisions.
- Executing commands in WSL2 and Docker Desktop.
- Interpreting test output and fixing defects.
- Protecting confidential assessment materials.
- Managing Git branches, commits and merges.
- Verifying behavior against the simulated Core.

This log summarizes collaboration; it is not a verbatim
transcript of all ChatGPT prompts and responses.

## 13. Known limitations

- Not every Core failure scenario was exercised end to end.
- GitHub Actions execution of the new Docker job is pending.
- A non-blocking Starlette/httpx warning remains.
- Local Docker and Core setup are required for full E2E.

## 14. Git commit evidence

The following history was obtained from Git:

dbcfae8 | 2026-11-17 | merge: integrate P007 data ingestion and quality
9d4b901 | 2026-11-17 | feat(data): add policy CSV ingestion, quality checks and SQL KPIs
3354113 | 2026-11-17 | merge: integrate claims HTTP API feature
9f232fa | 2026-11-17 | feat(api): implement claims HTTP endpoints and OpenAPI contract
e6466aa | 2026-11-17 | merge: integrate claims application service P005
9fc68de | 2026-11-17 | feat(claims): implement application service and SQLite persistence
b540343 | 2026-11-16 | fix(domain): support filing datetime from claims API
8bffd9a | 2026-11-16 | Merge pull request #3 from viejoedwinsierra/feature/004-core-http-client
ea7e529 | 2026-11-16 | Merge remote-tracking branch 'origin/develop' into feature/004-core-http-client
e2eb553 | 2026-11-16 | Merge pull request #2 from viejoedwinsierra/feature/003-claims-business-rules
4d2908e | 2026-11-16 | feat(infrastructure): add insurance core HTTP client
2bbbf81 | 2026-11-16 | feat(domain): integrate claims validation rules R1-R8
3fa605e | 2026-11-16 | feat(domain): normalize core contracts and enforce insured identity
299c93d | 2026-11-16 | docs(architecture): document policy-scoped R8 identity
5b91efc | 2026-11-16 | style(domain): normalize line endings in duplicate rules
fe672f4 | 2026-11-16 | feat(domain): implement policy-scoped duplicate detection R8
1593947 | 2026-11-16 | docs(architecture): propose claim duplicate detection ADR
4d1a34f | 2026-11-16 | feat(domain): implement policy rules R1 R2 R5 and coverage tests
4dd6842 | 2026-11-16 | test(domain): define policy validation rules R1 R2 R5
c4e3840 | 2026-11-16 | test(domain): expand date rule boundary coverage
8610b5e | 2026-11-16 | feat(domain): implement date validation rules R3 R4 R6 R7
75498c3 | 2026-11-16 | test(domain): define date validation boundary cases
bf2020a | 2026-11-16 | Merge pull request #1 from viejoedwinsierra/feature/002-ci-foundation
dad1163 | 2026-11-16 | ci: establish Python lint and automated test pipeline
d5865eb | 2026-11-16 | merge: integrate legacy baseline into develop
9fde917 | 2026-11-16 | chore: establish claims service project structure
d14fe5f | 2026-11-16 | chore: exclude confidential assessment materials
0dd288e | 2026-11-16 | chore: initialize legacy validation project structure
6f09538 | 2026-11-16 | Initial commit
