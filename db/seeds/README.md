# db/seeds

Datos de **desarrollo** para poblar la base local. ⚠️ **Todo es mock** (`is_mock = true`).

Orden de aplicación (tras correr las migraciones de `db/migrations`):

```bash
psql "$DATABASE_URL" -f db/migrations/0001_initial_schema.sql
psql "$DATABASE_URL" -f db/seeds/0001_seed_mock_premier_league.sql
```

En Fase 2, los seeds reales se generarán desde el pipeline de ingesta a partir de
proveedores autorizados; estos seeds mock se mantienen solo para pruebas locales y
para los entornos de demo claramente etiquetados.
