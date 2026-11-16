# ASTRA VITAL — Edición Académica (Python Flask + SQLite)

**Equipo:** NYXARA NOVA — Etner Therry Rios Vasquez, Jeanfranco Alfredo Ibarra Kocfú, Darlin Saldaña Pinedo, Máximo Fabrizzio Espinoza Peche.
**Origen:** proyecto ASTRA VITAL presentado oficialmente al NASA Space Apps Challenge 2026 (Trujillo, Perú) el 15/11/2026.
**Esta edición:** adaptación universitaria posterior, construida con Python Flask y SQLite. **No es la versión que se presentó a la NASA** (aquella fue una aplicación web estática: https://github.com/Etner249/astra-vital).

## Objetivo general
Desarrollar una aplicación web con Python Flask y SQLite que permita registrar astronautas, misiones y signos vitales, generar y gestionar alertas explicables de salud, y controlar el acceso por roles, conservando la identidad y el fundamento científico de ASTRA VITAL.

## Objetivos específicos
1. Diseñar una base de datos SQLite normalizada (6 tablas) con claves foráneas, restricciones e índices.
2. Implementar CRUD completo para usuarios, astronautas, misiones, mediciones y alertas.
3. Implementar autenticación (registro, login, logout) y autorización por roles en el backend (Administrador, Doctor/Especialista, Operador).
4. Reutilizar el motor de reglas de ASTRA VITAL (portado de JavaScript a Python) para generar alertas persistidas.
5. Aplicar seguridad: hash de contraseñas, CSRF, validación, cookies seguras, cabeceras de seguridad, auditoría.
6. Verificar el sistema con pruebas automatizadas (pytest) y desplegarlo en Render.

## Alcance y límites
- Prototipo educativo: **no es un dispositivo médico** y no diagnostica.
- Astronautas y mediciones de demostración son **sintéticos** (marcados `is_synthetic`).
- Los datos de NASA OSDR (OSD-575, OSD-569) son valores de laboratorio pre/post vuelo de Inspiration4, **no** signos vitales continuos en vuelo.
- En Render se usa el plan gratuito: **SQLite no persiste** entre reinicios/redespliegues (ver DEPLOYMENT_GUIDE.md).

## Cumplimiento de requisitos del curso
| Requisito | Dónde se cumple |
|---|---|
| Backend Python Flask | `app/__init__.py` (app factory, blueprints `auth`, `main`, `crud`) |
| SQLite + ORM | `app/models.py` (Flask-SQLAlchemy), `docs/academic/schema.sql` |
| Tablas users, astronauts, missions, health_measurements, health_alerts, audit_logs | `app/models.py` |
| PK, FK, restricciones, índices, relaciones | `schema.sql`, DATABASE_DESIGN.md |
| CRUD completo | `app/crud.py`; pruebas `tests/test_crud.py` |
| Registro, login, logout | `app/auth.py`; `tests/test_auth.py` |
| Roles y control de acceso en backend | `app/decorators.py`; `tests/test_authorization.py` |
| Hash de contraseñas, CSRF, validación | `app/models.py`, Flask-WTF, `app/forms.py`; `tests/test_security.py` |
| Usuario admin inicial seguro | comandos `flask create-user` / `flask bootstrap` (variables de entorno) |
| Pruebas pytest | 101 pruebas, TEST_REPORT.md |
| Despliegue GitHub + Render | `render.yaml`, `gunicorn.conf.py`, DEPLOYMENT_GUIDE.md |
| Documentación y evidencias | `docs/academic/`, `docs/academic/evidence/` |
