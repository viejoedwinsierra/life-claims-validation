# ADR-001: Identificación de reclamaciones duplicadas

## Estado

Aceptado para la prueba técnica.

## Contexto

La regla R8 exige detectar reclamaciones duplicadas del
mismo asegurado y evento.

El sistema también debe distinguir los reintentos técnicos
de nuevas solicitudes que representan el mismo evento.

## Decisión

Separar dos mecanismos independientes:

1. Idempotencia técnica por identificador de solicitud.
2. Duplicidad de negocio por identidad del evento asegurado.

La implementación actual utiliza SQLite.

## Idempotencia técnica

La clave `id_solicitud` identifica una solicitud.

El repositorio calcula `payload_hash` mediante SHA-256
sobre la representación JSON normalizada para serialización,
con claves ordenadas.

Resultados:

- Misma solicitud y mismo contenido: `ALREADY_EXISTS`.
- Misma solicitud y contenido diferente: `PAYLOAD_CONFLICT`.
- Solicitud nueva: continúa la reserva del evento.

## Identidad del evento de negocio

La identidad provisional del evento se compone de:

1. Número de póliza.
2. Tipo de documento del asegurado.
3. Número de documento del asegurado.
4. Fecha del siniestro.
5. Tipo de reclamación.

La función `event_identity` construye esta identidad.

El repositorio genera `business_event_key` mediante SHA-256.

Esta identidad permite diferenciar reclamaciones
correspondientes a pólizas distintas.

## Control de duplicados

La reserva utiliza restricciones de unicidad SQLite
y `INSERT ... ON CONFLICT DO NOTHING`.

Cuando existe un evento equivalente:

- Si el original está `REGISTERED`, se persiste un
  rechazo de la nueva solicitud con motivo `R8`.
- Si el original sigue en procesamiento o pendiente,
  la aplicación devuelve `IN_PROGRESS`.
- Si coincide `id_solicitud`, se aplica primero
  la semántica de idempotencia técnica.

La operación de rechazo por duplicidad utiliza
`BEGIN IMMEDIATE` para controlar la escritura concurrente.

## Consecuencias

Ventajas:

- Reintentos técnicos no crean nuevas reclamaciones.
- Duplicados de negocio pueden rechazarse con R8.
- Los rechazos R8 mantienen trazabilidad por solicitud.
- La identidad de negocio está separada del ID técnico.

Limitaciones:

- La identidad del evento es provisional.
- Debe validarse el tratamiento de múltiples amparos
  asociados a un mismo siniestro.
- SQLite tiene limitaciones de concurrencia de escritura.
- No existe reconciliación automática con el Core.
- No se ha implementado PostgreSQL.

## Evolución futura

Evaluar PostgreSQL según requisitos de escalabilidad.

Confirmar con negocio la identidad definitiva del evento,
especialmente cuando existen múltiples amparos.

Definir reconciliación de operaciones cuyo resultado
en el Core sea incierto.

Estas mejoras no forman parte de la implementación actual.

## Referencias

- `src/life_claims/domain/duplicate_rules.py`
- `src/life_claims/infrastructure/sqlite_claims_repository.py`
- `docs/arquitectura/ADR-002-persistencia-sqlite.md`
- `docs/arquitectura/ADR-003-integracion-core.md`
