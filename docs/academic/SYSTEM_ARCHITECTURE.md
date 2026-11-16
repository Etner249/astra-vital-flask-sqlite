# Arquitectura del sistema

## Vista general
```
Navegador (HTML5 + CSS3 + JS, identidad ASTRA VITAL)
        │  HTTPS (Render)  · cookies de sesión HttpOnly/Secure · token CSRF en cada formulario
        ▼
Gunicorn (2 workers)  →  Flask app factory (app/__init__.py)
        │                 ├─ Blueprint auth  (login, registro, logout, ajustes)
        │                 ├─ Blueprint main  (dashboard, riesgos, datos NASA, reportes, auditoría)
        │                 └─ Blueprint crud  (astronautas, misiones, mediciones, alertas, usuarios)
        │                 Flask-Login (sesiones) · Flask-WTF (formularios + CSRF) · decorador permission_required
        ▼
Capa de servicios (app/services.py)  ── Motor de reglas (app/engine.py, port de src/engine.js)
        ▼
Flask-SQLAlchemy ORM (app/models.py)
        ▼
SQLite (archivo; PRAGMA foreign_keys=ON, journal WAL)
```

## Estructura del proyecto
| Ruta | Contenido |
|---|---|
| `app/__init__.py` | App factory, extensiones, cabeceras de seguridad, manejadores de error, comandos CLI (`init-db`, `create-user`, `seed-demo`, `bootstrap`) |
| `app/config.py` | Configuración (desarrollo, producción, pruebas); ruta SQLite por `DATABASE_PATH` |
| `app/models.py` | 6 modelos ORM con restricciones |
| `app/forms.py` | Formularios WTForms con validaciones |
| `app/decorators.py` | Matriz de permisos y decorador `permission_required` |
| `app/auth.py`, `app/main.py`, `app/crud.py` | Rutas (blueprints) |
| `app/engine.py` | Motor de alertas explicable |
| `app/services.py` | Auditoría y generación/persistencia de alertas |
| `app/seed.py` | Datos sintéticos de demostración |
| `app/templates/`, `app/static/` | Vistas Jinja2, CSS y JS (reutilizados del proyecto original) |
| `tests/` | 101 pruebas pytest |
| `render.yaml`, `gunicorn.conf.py`, `Procfile` | Despliegue |

## Tecnologías
Python 3 · Flask 3.1 · Flask-SQLAlchemy 3.1 / SQLAlchemy 2 · Flask-Login 0.6 · Flask-WTF 1.3 / WTForms · Werkzeug (hash scrypt) · SQLite 3 · Gunicorn · pytest · HTML5/CSS3/JavaScript (gráficos SVG propios, sin librerías externas) · GitHub · Render.

## Flujo de una medición
1. Operador/Doctor/Admin envía el formulario (con token CSRF).
2. WTForms valida rangos y coherencia (p. ej., diastólica < sistólica; al menos un signo vital).
3. Se guarda en `health_measurements` (SQLite aplica además restricciones CHECK y FK).
4. `generate_alerts()` ejecuta el motor: umbrales documentados + línea base personal (≥2 DE sobre las primeras 7 mediciones); consolida un hallazgo por indicador.
5. Las alertas se guardan en `health_alerts` con explicación, acción sugerida, cuándo contactar al equipo médico y fuente.
6. Se registra la acción en `audit_logs`.

## Seguridad
- Contraseñas con hash (Werkzeug `generate_password_hash`, scrypt con sal); nunca en texto plano.
- CSRF en todos los formularios y acciones POST (incluidas eliminaciones y logout).
- Autorización en el backend por permiso (`permission_required`), no solo ocultando botones; respuestas 403.
- Cookies de sesión HttpOnly, SameSite=Lax y Secure en producción; `SECRET_KEY` generada por Render.
- Validación de entradas en formularios y en la base de datos (CHECK, FK, UNIQUE).
- Redirecciones seguras (bloqueo de *open redirect*), mensajes de login genéricos.
- Cabeceras: Content-Security-Policy, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy.
- Páginas de error propias (400/403/404/500) sin trazas internas.
- Registro de auditoría de inicios de sesión y operaciones de escritura.
