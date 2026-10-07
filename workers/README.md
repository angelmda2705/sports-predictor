# workers — Procesamiento batch (Python)

> 🚧 Placeholder de estructura. Se implementa en **Fase 2** (pipeline real + predicción).

Jobs orquestados por el scheduler. Operan en el plano de cómputo (offline), separados
de la API de servicio.

## Jobs previstos

| Job | Función |
|---|---|
| `ingest` | Extrae de un `SportsDataProvider`, valida, limpia, estandariza y persiste un snapshot. |
| `build_features` | Construye features **point-in-time** y las guarda en el feature store. |
| `train` | Entrena/evalúa con validación temporal; registra en MLflow. |
| `predict` | Predice próximos partidos; calibra; persiste `prediction`. |
| `evaluate` | Tras cada partido: calcula Brier/LogLoss/errores y llena `prediction_outcome`. |
| `monitor_drift` | Vigila cambios de distribución en los datos de entrada. |

Todos los jobs registran su corrida en la tabla `provider_run` / logs estructurados.
