# apps/web — Frontend (Next.js 14 + React + TS + Tailwind)

App Router, TypeScript estricto, Tailwind con **modo oscuro** (estrategia `class`,
sin parpadeo). Consume la API de `apps/api`.

## Estado

- ✅ **UI base de Fase 1**: layout, header con toggle de tema, footer con avisos de
  uso responsable.
- ✅ **Dashboard** (`/`): próximos partidos desde `GET /matches`, filtros por deporte,
  estados de carga/vacío/error y **banner de datos mock**.
- ✅ **Login/Registro** (`/login`): contra `/auth`, con `AuthProvider` (contexto) que
  guarda tokens en `localStorage` y carga `/auth/me`.
- ✅ **Ficha de partido** (`/matches/[id]`): detalle desde `GET /matches/{id}`, con
  sección de predicción reservada (se habilita con los endpoints de predicción).
- 🚧 Pendiente: refresh automático de tokens, favoritos, comparador, pantalla de
  predicciones, dashboard de rendimiento del modelo.

## Estructura

```
src/
  app/
    layout.tsx           Layout raíz + script anti-parpadeo de tema + avisos
    page.tsx             Dashboard (próximos partidos)
    login/page.tsx       Login / registro
    matches/[id]/page.tsx  Ficha de partido
    globals.css          Tailwind + base claro/oscuro
  components/
    AuthProvider.tsx     Contexto de auth (login/register/logout)
    Header.tsx           Navegación + estado de sesión
    ThemeToggle.tsx      Modo oscuro
    MatchCard.tsx        Tarjeta de partido
    MockBanner.tsx       Aviso de datos de prueba
  lib/
    api.ts               Cliente HTTP (NEXT_PUBLIC_API_URL)
    types.ts             Tipos espejo de la API
    format.ts            Formato de fechas y etiquetas
```

## Desarrollo

Requiere el backend (`apps/api`) corriendo en `http://localhost:8000`.

```bash
npm install
cp .env.example .env.local         # ajusta NEXT_PUBLIC_API_URL si hace falta
npm run dev                        # http://localhost:3000
npm run build                      # build de producción (verificación de tipos)
```

## Reglas de producto en la UI

- Predicciones siempre como **probabilidad + confianza**, nunca certezas.
- **Banner visible** cuando una vista contiene datos `is_mock`.
- Avisos de incertidumbre y uso responsable en el footer.
- Las claves de API **no** viven en el frontend; todo pasa por `apps/api`.
