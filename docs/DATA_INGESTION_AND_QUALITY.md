# Policy Data Ingestion and Quality

## Purpose
Load policy CSV data into SQLite for reproducible analytics.
The Core simulator remains authoritative for claims validation.

## Ingestion
- Source: polizas.csv
- Migration: datos/migrations/002_create_policy_raw.sql
- Tables: ingestion_batches, polizas_raw
- SHA-256 prevents repeated ingestion of identical files.
- RAW values and source row numbers are preserved.
- Duplicate policy records remain available for analysis.

## Data quality
- Missing values and exact duplicate rows
- Invalid dates and inverted coverage periods
- Nonstandard document types
- Invalid, negative and zero insured amounts

## SQL indicators
- 001_policy_distribution.sql: product and status
- 002_insured_value.sql: insured amount by product and channel
- 003_policy_validity.sql: coverage date quality
- 004_policy_completeness.sql: missing fields by product

Financial aggregation uses Python Decimal.
Date validation uses a Python SQLite function.

## Verified dataset
| Metric | Result |
|---|---:|
| RAW records | 4950 |
| Distinct policies | 4850 |
| Exact duplicates | 60 |
| Invalid start dates | 132 |
| Invalid end dates | 146 |
| Inverted coverage periods | 30 |
| Missing product | 10 |
| Missing insured name | 30 |
| Missing coverage | 25 |
| Valid financial records | 4871 |
| Excluded financial records | 79 |
| Total insured amount | 763460000000.00 |

The insured amount includes RAW duplicates.
Quality categories may overlap.

## Verification
Run: python -m pytest -q
Run: python -m ruff check src tests

## Confidentiality
The original CSV and local SQLite database are excluded from Git.
Integration tests use synthetic data.
