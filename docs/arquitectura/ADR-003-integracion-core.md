# ADR-003: HTTP integration with the Insurance Core

## Status

Accepted for the technical assessment.

## Context

The claims API depends on an external simulated
Insurance Core for operational policy information
and claim registration.

The Core and local SQLite persistence cannot participate
in a single atomic database transaction.

## Decision

Use synchronous HTTP/JSON communication through HTTPX.
Encapsulate Core operations in CoreClient.
Configure the endpoint through CORE_BASE_URL.
Send id_solicitud as the Idempotency-Key header
when registering a claim.

## Operations

- GET /api/v1/polizas/{numero_poliza}
- POST /api/v1/siniestros

A policy HTTP 404 is translated into None.
Other unsuccessful HTTP responses raise HTTPX exceptions.

## Timeout configuration

- Connection timeout: 3 seconds.
- Read timeout: 5 seconds.
- Write timeout: 3 seconds.
- Connection pool timeout: 3 seconds.

## Registration outcomes

### Successful registration

The Core returns numero_siniestro.
The application persists REGISTERED.

### Registration timeout

The application persists PENDING_CONFIRMATION.
This state does not imply that registration failed.

### Other technical failures

Non-timeout HTTP and transport failures are not
explicitly translated into persistent recovery states
by the current application service.

## Consequences

Positive:
- Core communication is isolated behind an adapter.
- HTTP timeouts are explicitly configured.
- Registration requests carry an idempotency key.
- Ambiguous registration timeouts preserve uncertainty.

Limitations:
- No automatic reconciliation process is implemented.
- No distributed transaction spans SQLite and the Core.
- Automatic retries are not implemented in CoreClient.
- Core support for the idempotency header must be
  distinguished from the client's act of sending it.

## Future evolution

Evaluate reconciliation of PENDING_CONFIRMATION records
using a Core-supported lookup mechanism.
Define bounded retries and operational observability.
Confirm end-to-end idempotency semantics with the Core.

These are proposals, not implemented capabilities.
