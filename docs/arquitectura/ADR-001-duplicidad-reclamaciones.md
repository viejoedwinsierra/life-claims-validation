# ADR-001: Identificación de reclamaciones duplicadas

## Estado
Propuesto.

## Contexto
La regla R8 exige detectar reclamaciones duplicadas del
mismo asegurado y del mismo evento.

La aplicación debe soportar solicitudes concurrentes,
reintentos y fallos de comunicación con el core externo.

## Decisión propuesta
1. Separar idempotencia técnica de duplicidad de negocio.
2. Definir una identidad canónica del evento.
3. Consultar reclamaciones existentes antes del registro.
4. Garantizar exclusión concurrente mediante PostgreSQL.
5. No asumir que un timeout del core significa que el
   registro externo falló.
6. No publicar datos personales ni el kit confidencial.

## Pendiente de confirmar
- Campos disponibles para identificar un evento.
- Si existe un identificador único de siniestro de origen.
- Semántica de reclamaciones del mismo evento y diferente amparo.
- Capacidades de consulta y reconciliación del core.

## Consecuencias
La regla R8 requerirá un puerto de persistencia y una
implementación transaccional.

La identidad definitiva del evento no se establecerá
hasta verificar el contrato del kit.

## Identidad provisional de reclamación

Para la detección de duplicidad R8 se propone una clave
compuesta por:

1. Número de póliza.
2. Tipo de documento del asegurado.
3. Número de documento del asegurado.
4. Fecha del siniestro.
5. Tipo de reclamación.

Esta combinación permite diferenciar reclamaciones
asociadas a pólizas distintas de un mismo asegurado.

El identificador `id_solicitud` se reserva para la
idempotencia técnica y no forma parte de la identidad
de negocio.

La identidad es provisional: requiere validación con
negocio, especialmente cuando existen varios amparos
para un mismo evento.

La comparación implementada en el dominio no garantiza
por sí sola exclusión concurrente. La persistencia deberá
incorporar mecanismos transaccionales en PostgreSQL.
