# ADR 0001 — Backend en FastAPI (Python)

- **Estado:** Aceptado
- **Fecha:** 2026-06-23

## Contexto

El proyecto es *data/ML-first*: el valor central son los modelos predictivos y el
pipeline de datos, ambos en Python (pandas, scikit-learn, XGBoost, MLflow, SHAP).
Se evaluó FastAPI (Python) vs NestJS (Node.js) para la capa de API.

## Decisión

Se usa **FastAPI**.

## Justificación

- **Cohesión de lenguaje con el ML:** API y modelos comparten objetos (DataFrames,
  modelos serializados) sin una frontera de serialización entre servicios.
- **Sin duplicar la lógica de features:** evitar reimplementar transformaciones en
  dos lenguajes (fuente de bugs y de fuga de datos sutil).
- **Pydantic v2** da validación de esquemas estricta, alineada con el requisito de
  tipado estricto y validación de entradas.
- **ASGI/async** suficiente para la carga de lectura del MVP (la API solo lee
  predicciones ya calculadas; el cómputo pesado vive en workers batch).

## Consecuencias

- El frontend sigue en Next.js/TypeScript; el contrato API se define con OpenAPI
  (generado por FastAPI) para tipar el cliente web.
- NestJS habría aportado un ecosistema web más maduro, pero a costa de un puente
  Python↔Node para el ML. Se acepta el trade-off a favor de la cohesión.

## Alternativas consideradas

- **NestJS (Node):** descartado por la frontera con el ML.
- **Django:** más pesado de lo necesario para una API de lectura desacoplada.
