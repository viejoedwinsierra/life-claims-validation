# P010 — Informe de evaluación de reclamaciones

## Alcance

- Fecha de evaluación: 2026-11-17
- Lote analítico: 1
- Ejecución consolidada: RUN_ID=2
- Origen: Core HTTP simulado
- Método: evaluación de solo lectura
- Reglas evaluadas: R1–R7
- R8: no evaluada (r8_source=NONE)

## Resultados consolidados

| Indicador | Cantidad | Porcentaje |
|---|---:|---:|
| Válidas | 193 | 62.87% |
| Rechazadas | 114 | 37.13% |
| Errores técnicos | 0 | 0.00% |
| **Total** | **307** | **100 %** |

## Infracciones por regla

| Regla | Reclamaciones con infracción |
|---|---:|
| R1 | 15 |
| R2 | 35 |
| R3 | 18 |
| R4 | 12 |
| R5 | 18 |
| R6 | 10 |
| R7 | 6 |

Una reclamación puede presentar más de una infracción.

## Trazabilidad

- RUN_ID=1: primera evaluación HTTP, conservada.
- RUN_ID=2: consolidación de resultados originales y reintentos.
- Se reutilizaron 290 resultados y se recuperaron 17 reclamaciones.
- No se registraron nuevos siniestros en el Core.

## Limitaciones

- R8 no se evaluó contra el historial transaccional.
- Los resultados no constituyen una validación completa de R1–R8.
- El Core HTTP utiliza fallos artificiales; RUN_ID=1 conserva los errores observados.
