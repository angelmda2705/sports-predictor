# Licenciamiento de fuentes de datos

> **Regla:** ningún proveedor de datos se integra en producción sin registrar aquí
> su licencia, sus términos de uso y la fecha de revisión. No se hace scraping de
> fuentes cuyos Términos de Servicio lo prohíban.

| Proveedor | Deporte | Modelo | Requiere clave | Términos / riesgo | Estado | Revisado |
|---|---|---|---|---|---|---|
| **nflverse / nfl_data_py** | NFL | Open source | No | Datos abiertos (base nflfastR). Verificar atribución requerida. | Candidato principal NFL | Pendiente |
| **football-data.org** | Soccer | Free / pago | Sí | Free tier con límites de rate y cobertura. Revisar ToS de uso comercial. | Candidato MVP soccer | Pendiente |
| **API-Football (api-sports.io)** | Soccer | Pago | Sí | Suscripción de pago. Cobertura amplia (lineups, lesiones, xG). | Evaluar Fase 2 | Pendiente |
| **StatsBomb Open Data** | Soccer | Open | No | Licencia de datos abiertos con condiciones de atribución/no comercial en parte. **Leer licencia antes de uso comercial.** | Evaluar | Pendiente |
| **Understat / FBref (Opta)** | Soccer | Scraping | No | ⚠️ **Posible violación de ToS.** No integrar sin revisión legal explícita. | Bloqueado por defecto | Pendiente |
| **The Odds API** | Transversal | Free / pago | Sí | Cuotas multi-casa. Free tier limitado. | Evaluar Fase 2 | Pendiente |
| **Open-Meteo** | Transversal | Free | No | Clima histórico y pronóstico. Licencia abierta. | Candidato | Pendiente |
| **DVOA (Football Outsiders)** | NFL | Propietario | — | Métrica propietaria. Solo con licencia explícita. | Bloqueado por defecto | Pendiente |

## Decisión actual del proyecto (2026-06-23)

- La selección de proveedores de pago se difiere a **Fase 2**.
- **Fase 1 usa exclusivamente `MockSportsDataProvider`** (datos `is_mock=true`).
- Antes de integrar cualquier fuente real se actualiza la columna "Revisado" con la
  fecha y el responsable, y se adjunta el enlace a los Términos de Servicio vigentes.
