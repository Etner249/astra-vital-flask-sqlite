# ASTRA VITAL — Auditoría técnica final

Fecha: 2026-11-16. Alcance: backend `astra-vital-flask-sqlite` (main), frontend `astra-vital` (main b9da8f8), despliegue Render (commit 8d6bd9b) y GitHub Pages.

## Verificado

| Área | Resultado |
|---|---|
| Estructura Flask | App factory, blueprints `api` (/api/v1), `auth`, `main`, `crud`; config por entorno |
| SQLite | 7 tablas, 8 índices, CHECK de rangos, FK con CASCADE / SET NULL / RESTRICT, `foreign_keys=ON`, WAL |
| CRUD | Usuarios, astronautas, misiones, mediciones, alertas (API e interfaz Flask) |
| Autenticación | scrypt; tokens Bearer 256 bits, solo SHA-256 en BD, expiración 8 h, revocación en logout; sesiones Flask-Login HttpOnly/SameSite/Secure |
| Autorización | Matriz de permisos aplicada en backend (403); probada por rol en 51 pruebas |
| CSRF / CORS | Flask-WTF en la interfaz HTML; API sin cookies; CORS solo a `https://etner249.github.io` |
| Fuerza bruta | 10 fallos / 5 min por IP en login API |
| Cuentas demo | Idempotentes, sin secretos, usuarios solo lectura, sin cambio de contraseña, datos sintéticos protegidos, emails/IP enmascarados |
| Secretos | SECRET_KEY y contraseñas privadas generadas por Render; ninguna en el repositorio |
| Copia NASA | `/nasa-2026/index.html` con SHA-256 idéntico al commit 8df773b; rama y release de respaldo |
| Pruebas | 136 pytest, 10 motor JS, 84 E2E — todas aprobadas |
| Producción | `/api/v1/health` ok; Pages carga login; servicio Render Live |

## Hallazgos y riesgos

| # | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| 1 | Alta (operativa) | Render Free: SQLite efímero; reinicio/redeploy/suspensión borran los datos (verificado en logs) | Disco persistente (plan pago) o PostgreSQL gestionado |
| 2 | Media | Límite de login en memoria por proceso (2 workers → no compartido) | Redis u otro almacén compartido |
| 3 | Baja | 29 DeprecationWarning de WTForms (choices como tuplas) | Migrar antes de WTForms 3.4 |
| 4 | Baja | Pruebas sensibles a `CORS_ORIGINS`/`DATABASE_PATH` exportadas | Aislar configuración de pruebas (fixture que limpie el entorno) |
| 5 | Baja | Arranque en frío ~50 s tras inactividad | Aviso ya mostrado en el login; plan pago lo elimina |
| 6 | Informativa | Umbrales y convenciones del motor sin validación clínica | Revisión por profesionales de salud |
| 7 | Pendiente | Verificación manual del rol Médico en producción no completada (sí verificado en local y en pruebas) | Iniciar sesión como Médico en producción |

No se encontraron secretos en el repositorio ni contraseñas privadas en la interfaz.
