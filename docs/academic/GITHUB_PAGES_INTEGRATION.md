# Integración GitHub Pages ↔ Render (rama `api-integration`)

**Objetivo:** que https://etner249.github.io/astra-vital/ (URL enviada a la NASA) abra ASTRA VITAL con *NASA Evaluator Access* y use este backend Flask + SQLite como “ground store”.
**Estado (16/11/2026):** implementado y verificado en entorno de vista previa. **No publicado en `main`** de ninguno de los dos repositorios (pendiente de autorización).

## Ramas y servicios
| Pieza | Ubicación |
|---|---|
| Frontend (10 módulos originales + login + Mission Control) | `Etner249/astra-vital`, rama `academic-integration` |
| Copia congelada de la entrega NASA | `nasa-2026/index.html` (SHA-256 `2f0c62f7…4019713`, idéntico al commit `8df773b`) · rama `backup/nasa-submission-2026-11-15` |
| API v1 (este repo) | rama `api-integration` (`app/api.py`) |
| Backend de prueba | Render `astra-vital-api-preview` (Blueprint `render.preview.yaml`) → https://astra-vital-api-preview.onrender.com |
| Frontend de prueba | https://etner249.github.io/astra-vital-preview/ (mismo origen `https://etner249.github.io` que la URL oficial) |

## Diseño
- **API `/api/v1`**: health, demo-accounts, auth/login|logout|me, missions, astronauts, measurements (9 indicadores + FR), alerts (revisión), users, audit, reports/summary.
- **Autenticación Bearer**: token aleatorio de 256 bits; en SQLite solo su SHA-256 (`api_tokens`), expira a las 8 h, se revoca al cerrar sesión. Sin cookies → funciona entre sitios y CSRF no aplica; la API ignora la cookie de sesión.
- **CORS**: solo el origen exacto `CORS_ORIGINS` (por defecto `https://etner249.github.io`); otros orígenes → 403 sin cabeceras CORS. Sin `Allow-Credentials`.
- **Permisos**: misma matriz y mismos límites de cuentas demo que la interfaz HTML. Errores JSON con explicación.
- **Login**: límite de 10 intentos fallidos / 5 min por IP.
- **Frontend**: CSP `connect-src` limitado al origen de la API; token en `sessionStorage`; cola offline en `localStorage` enviada en lotes de 5 cuando el enlace es AOS.
- **Indicadores originales**: nuevas columnas `sleep_hours`, `exercise_min`, `fatigue`, `mood`, `glucose` con CHECK y reglas portadas de `src/engine.js`.

## Resultados
- pytest: **136 aprobadas, 0 fallidas** (`evidence/pytest-output.txt`); 34 nuevas en `tests/test_api.py` y `tests/test_engine.py`.
- Playwright local (Pages simulado + Flask local): **72/72**, 0 errores JS (`evidence/e2e_local/`).
- Remoto (GitHub Pages → Render preview), con las 3 cuentas en el navegador: 10 módulos originales por rol, permisos (403/ocultos), log + sincronización, cola LOS→AOS, revisión de alertas, edición, CRUD de astronautas y misiones, bloqueo de borrado de datos sintéticos, usuarios solo lectura, auditoría con IP oculta, 0 errores JS (`evidence/24*`).
- Persistencia: los registros creados por el operador fueron visibles para médico y administrador en otras sesiones (SQLite compartido). Tras **reiniciar** el servicio, el log muestra “No SQLite database… creating a new one” y el frontend vuelve al login con “Tu sesión expiró o el servidor se reinició” (`evidence/24h`, `24i`).

## Pasos para publicar (requieren autorización)
1. Merge `api-integration` → `main` (este repo) y deploy de `astra-vital-academic` (añade la API; la UI Flask no cambia).
2. Merge `academic-integration` → `main` en `astra-vital` (index.html ya apunta a `https://astra-vital-academic.onrender.com/api/v1`).
3. Verificar https://etner249.github.io/astra-vital/ y `/nasa-2026/`.
4. Opcional: borrar `astra-vital-preview` y el servicio `astra-vital-api-preview`.
