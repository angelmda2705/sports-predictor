# apps/api — Capa de servicio (FastAPI)

API de la plataforma. Sigue Clean Architecture (dominio → aplicación → infraestructura
→ interfaz). Por defecto arranca con repositorios **en memoria** (sin Postgres),
para desarrollo local; el cableado SQLAlchemy/Postgres por request es el siguiente incremento.

## Estado

- ✅ **Autenticación** (incremento de Fase 1): registro, login, refresh token
  **rotatorio con detección de reuso**, logout, `/auth/me`, RBAC (`/auth/admin/ping`).
  - Argon2id para contraseñas, JWT (HS256) para access tokens, refresh opacos (SHA-256 en BD).
  - Rate limiting en endpoints de auth, CORS restrictivo, mensajes anti-enumeración,
    guarda que rechaza secreto débil/por-defecto en producción.
  - Repos en memoria (dev/tests) + adaptador SQLAlchemy (Postgres/SQLite) probado.
- ✅ **Catálogo** (incremento de Fase 1): competiciones, equipos y partidos sobre
  datos mock etiquetados, con filtros (deporte/competición/equipo/estado/fecha),
  búsqueda y paginación. Lectura pública.
- 🚧 Pendiente: wiring DB sesión-por-request, endpoints de predicción, límites por plan.

## Arquitectura interna

```
src/
  config.py              Settings (pydantic-settings) + guarda de secreto en prod
  domain/                Entidades (User, Role, Plan) y errores de dominio
  application/
    ports.py             Puertos de repositorio (Protocols)
    auth_service.py      Casos de uso de auth (registro/login/refresh/logout)
    security/            Argon2 (password.py) + JWT/refresh (tokens.py)
  infrastructure/
    memory/              Repos en memoria (dev/tests)
    db/                  Modelos + repos SQLAlchemy (producción)
  interface/
    schemas.py           Esquemas Pydantic de E/S
    deps.py              Auth de la petición, RBAC, rate limit
    errors.py            Manejo centralizado de errores → HTTP
    routers/auth.py      Endpoints /auth/*
  main.py                create_app() (composición) + /health
tests/                   31 pruebas (unit + integración API + integración ORM)
```

## Desarrollo

```bash
# Entorno virtual (ya creado en .venv/ durante el bootstrap)
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,postgres]"   # o instalar deps sueltas

# Pruebas
.venv/Scripts/python -m pytest -q

# Servidor de desarrollo (repos en memoria)
.venv/Scripts/python -m uvicorn src.main:app --reload
# Docs interactivas: http://localhost:8000/docs
```

## Endpoints de auth

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| POST | `/auth/register` | Alta de usuario | — (rate limited) |
| POST | `/auth/login` | Devuelve access + refresh | — (rate limited) |
| POST | `/auth/refresh` | Rota el refresh token | refresh token |
| POST | `/auth/logout` | Revoca el refresh token | refresh token |
| GET | `/auth/me` | Perfil del usuario actual | Bearer access |
| GET | `/auth/admin/ping` | Ejemplo RBAC solo-admin | Bearer access (admin) |
| GET | `/health` | Healthcheck | — |

## Endpoints de catálogo (lectura pública, datos mock)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/competitions?sport=` | Lista competiciones (filtro por deporte) |
| GET | `/competitions/{code}` | Detalle de una competición |
| GET | `/competitions/{code}/teams` | Equipos de una competición |
| GET | `/teams/{code}` | Detalle de un equipo |
| GET | `/matches?sport=&competition=&team=&status=&date_from=&date_to=&q=&limit=&offset=` | Partidos con filtros, búsqueda y paginación |
| GET | `/matches/{id}` | Detalle de un partido |

> Todas las respuestas de catálogo incluyen `is_mock`; las listas de partidos
> añaden `contains_mock` para que la UI muestre el banner de datos de prueba.
