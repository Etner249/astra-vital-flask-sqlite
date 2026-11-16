# Integración GitHub Pages ↔ Render (rama `api-integration`)

**Objetivo:** que https://etner249.github.io/astra-vital/ (URL enviada a la NASA) abra ASTRA VITAL con *NASA Evaluator Access* y use este backend Flask + SQLite como “ground store”.
**Estado (16/11/2026, 12:20 hora de Lima):** **publicado en producción** con autorización del equipo.
- `astra-vital-flask-sqlite` `main` = `8d6bd9b` → desplegado en Render `astra-vital-academic` (log: "Demo accounts ready: 3 created"; `GET /api/v1/health` → `status: ok`).
- `astra-vital` `main` = `d32e52c` → GitHub Pages (`pages-build-deployment` #4 OK). https://etner249.github.io/astra-vital/ muestra NASA Evaluator Access y usa `https://astra-vital-academic.onrender.com/api/v1`.
- Respaldo: rama `backup/nasa-submission-2026-11-15` y tag/release `nasa-submission-2026-11-15` → `8df773b`; `/nasa-2026/` con SHA-256 idéntico.
- Verificado en la URL oficial: Operador (10 módulos, 9 indicadores guardados en SQLite, cola LOS→AOS, sin edición/borrado, perfil solo lectura, `#users` bloqueado) y Administrador (10 módulos + 5 nuevos, CRUD de astronautas y misiones, bloqueo de borrado de datos sintéticos, usuarios solo lectura, auditoría con IP oculta); 0 errores JS (`evidence/25*`). El rol Médico se verificó en la vista previa con el mismo código y en las pruebas automáticas.
- Entornos de vista previa conservados (`astra-vital-preview`, `astra-vital-api-preview`).

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

## Pasos de publicación (ejecutados el 16/11/2026)
1. Merge `api-integration` → `main` (este repo) y deploy de `astra-vital-academic` (añade la API; la UI Flask no cambia).
2. Merge `academic-integration` → `main` en `astra-vital` (index.html ya apunta a `https://astra-vital-academic.onrender.com/api/v1`).
3. Verificar https://etner249.github.io/astra-vital/ y `/nasa-2026/`.
4. Opcional: borrar `astra-vital-preview` y el servicio `astra-vital-api-preview`.

## Limitación de persistencia (Render gratuito)
SQLite vive en el disco efímero de la instancia gratuita: **cada reinicio, redespliegue o suspensión por inactividad (~15 min sin tráfico) borra la base** y `flask bootstrap` la recrea con los datos sintéticos y las 3 cuentas demo. Las sesiones abiertas vuelven al login ("Tu sesión expiró o el servidor se reinició"). Los registros pendientes en la cola del navegador no se pierden: se reenvían en la siguiente sincronización. Para persistencia real: plan de pago con Persistent Disk (`DATABASE_PATH=/var/data/astra_vital.db`) o una base gestionada.
