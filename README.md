# sports-predictor

Plataforma de **predicciones deportivas probabilísticas** (fútbol soccer y NFL) construida de punta a punta: ingesta de datos, modelos estadísticos, evaluación honesta con validación temporal, API REST y tablero web.

> Estas predicciones son **estimaciones de probabilidad**, no certezas ni "picks seguros". No es una casa de apuestas. El rendimiento pasado no garantiza resultados futuros.

**Estado:** proyecto personal en desarrollo. Soccer funciona de extremo a extremo con datos reales abiertos; NFL está planteado en el diseño pero aún no implementado.

## Qué hace

- Estima la probabilidad de **local / empate / visitante** de cada partido con dos modelos: **Elo** y **Dixon-Coles**.
- Evalúa los modelos con **validación walk-forward**: entrena solo con el pasado y predice jornada por jornada, como ocurriría en la vida real.
- Expone resultados y predicciones por una **API FastAPI** con autenticación, y los muestra en un **tablero Next.js** (partidos, historial y rendimiento).
- Marca cuando el contexto reduce la confianza (por ejemplo, equipos ya clasificados o eliminados, que el modelo no puede ver).

## Resultados del backtest (reproducibles)

Premier League, temporada 2023-24, 380 partidos, reentrenando antes de cada jornada:

| Modelo | Accuracy | Brier | LogLoss |
|---|---|---|---|
| Elo | 0.5658 | 0.5576 | 0.9462 |
| Dixon-Coles | 0.5684 | 0.5499 | 0.9337 |

Dixon-Coles mejora el Brier por poco. El resultado 1X2 en fútbol tiene un techo natural de precisión cercano a 53-56 %, incluso para las casas de apuestas, por eso el proyecto se mide con **Brier, LogLoss y calibración** y no promete aciertos altos.

```bash
cd apps/api
python -m scripts.compare_models
```

## Principios de diseño

1. Todo es probabilidad, nada es certeza.
2. **Cero fuga temporal:** las variables se calculan con información disponible en ese momento, con una prueba anti-fuga en el CI.
3. **Sin datos inventados:** los datos de prueba siempre van etiquetados (`is_mock=true`).
4. **Reproducibilidad:** cada predicción queda ligada a la versión del modelo y a la fotografía de datos con que se hizo.
5. **Transparencia:** el panel de rendimiento no oculta los fallos.

## Arquitectura

```
apps/web         Next.js + React + TypeScript + Tailwind (presentación)
apps/api         FastAPI por capas: domain / application / infrastructure / interface
packages/ml      Núcleo de modelos: Elo, Dixon-Coles, métricas, guardia anti-fuga
packages/shared  Contratos compartidos
db               Migraciones y datos de ejemplo etiquetados
docs             Documento técnico, decisiones de arquitectura (ADR) y licencias de datos
```

## Pruebas

| Módulo | Pruebas |
|---|---|
| `apps/api` | 78 (autenticación, catálogo, predicciones, rendimiento, repositorios, configuración) |
| `packages/ml` | 43 (Elo, Dixon-Coles, métricas, anti-fuga, proveedores) |

El CI (GitHub Actions) corre `ruff`, `mypy` y `pytest` sobre el módulo de modelos.

## Cómo correrlo

```bash
# API
cd apps/api
python -m venv .venv && .venv/Scripts/activate      # en Linux/Mac: source .venv/bin/activate
pip install -e ../../packages/ml -e ".[dev]"
cp ../../.env.example .env                          # y ajusta los valores
python -m pytest -q
python -m uvicorn src.main:app --port 8000

# Web
cd apps/web
npm install && npm run dev
```

## Datos

Soccer usa datos abiertos: calendarios de `openfootball` y resultados históricos internacionales del dataset de `martj42`. Ningún proveedor se integra sin revisar su licencia: ver [`docs/data-licenses.md`](docs/data-licenses.md). La integración con un proveedor de pago (API-Football) está soportada, pero requiere una clave propia y no se incluye ninguna.

## Documentación

- [Documento técnico del MVP](docs/DOCUMENTO_TECNICO_MVP.md)
- [Decisión: backend en FastAPI](docs/adr/0001-backend-fastapi.md)

## Licencia

Copyright (c) 2026 Ángel Mendiola. Todos los derechos reservados. El código se publica para evaluación profesional; no se concede licencia de uso, copia, modificación ni distribución sin autorización por escrito. Ver [`LICENSE`](LICENSE).
