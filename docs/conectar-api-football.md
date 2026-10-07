# Conectar el proveedor de pago (API-Football)

API-Football (api-sports.io) aporta lo que las fuentes abiertas no tienen:
**alineaciones confirmadas** y **lesiones** — justo lo que el modelo necesita para
afinar el contexto (rotaciones, bajas) en vez de solo inferirlo.

> 🔒 **Tu API key es un secreto.** No la compartas. El archivo `.env` donde la pones
> NO se sube a git (está en `.gitignore`). La aplicación la lee directamente; nadie
> más la ve.

## Pasos (5 minutos)

1. **Crea una cuenta y elige un plan** en:
   https://dashboard.api-football.com/
   - Hay un plan gratuito muy limitado para probar y planes de pago (desde ~unos
     pocos USD/mes) con más peticiones y alineaciones/lesiones.

2. **Copia tu API key** desde el panel (sección "My Access" / "API Key").

3. **Crea el archivo `apps/api/.env`** (en la carpeta del backend) con esta línea
   (reemplaza el valor por tu key real):

   ```
   API_FOOTBALL_KEY=tu_api_key_real_aqui
   ```

   > El backend se arranca desde `apps/api`, así que busca el `.env` ahí.
   > Alternativa: definir la variable de entorno `API_FOOTBALL_KEY` antes de iniciar.

4. **Reinicia la aplicación** (cierra y vuelve a abrir con el lanzador, o reinicia
   el backend).

5. **Verifica la conexión**: abre en el navegador

   ```
   http://localhost:8000/providers/status
   ```

   - Si ves `"configured": true, "connected": true` y los datos de tu cuenta (plan,
     peticiones del día), **la conexión funciona**. ✅
   - Si `"connected": false`, revisa que la key esté bien copiada y que tu plan esté
     activo (el mensaje de `error` te orienta).

## Qué queda listo (y qué sigue)

- ✅ Cliente de API-Football (estado de cuenta, **alineaciones**, **lesiones**,
  búsqueda de fixtures) con la key leída de forma segura desde `.env`.
- ✅ Endpoint `/providers/status` para verificar tu conexión.
- ⏭️ **Siguiente paso (cuando tu key esté activa):** conectar las alineaciones/lesiones
  reales al detector de contexto y a la predicción, para que "México podría rotar"
  se vuelva "México alinea suplentes: faltan X, Y, Z". Eso se prueba contigo y tu key.

## Nota de honestidad

No pude probar la llamada en vivo porque no tengo (ni debo tener) tu API key ni tu
cuenta. La integración está construida según la documentación de API-Football v3 y
el parseo está cubierto con pruebas usando payloads de ejemplo. La verificación real
la haces tú con el paso 5.
