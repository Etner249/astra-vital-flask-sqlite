# ASTRA VITAL — Academic Edition (Flask + SQLite)

Aplicación web universitaria de monitoreo de salud de astronautas, construida con **Python Flask y SQLite** por el equipo **NYXARA NOVA** (UPRIT, Trujillo – Perú).

> Adaptación académica **posterior** del proyecto ASTRA VITAL presentado al NASA Space Apps Challenge 2026. La versión presentada a la NASA es la app web estática de https://github.com/Etner249/astra-vital. Este no es un producto oficial de la NASA ni un dispositivo médico; los datos de demostración son sintéticos.

**Demo en vivo:** https://astra-vital-academic.onrender.com (plan gratuito de Render: la primera carga puede tardar ~50 s y la base de datos se reinicia en cada reinicio/despliegue).

## Acceso para evaluadores — NASA Evaluator Access

La pantalla de inicio de sesión muestra tres **cuentas públicas de demostración** (una por rol), con botones para copiar el correo y la contraseña y un botón **"Usar esta cuenta"** que rellena el formulario.

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin.demo@astravital.example` | `AstraDemo-Admin-2026` |
| Médico / Especialista | `medico.demo@astravital.example` | `AstraDemo-Medico-2026` |
| Operador | `operador.demo@astravital.example` | `AstraDemo-Operador-2026` |

**Cómo ingresar:** abre https://astra-vital-academic.onrender.com/login → elige una cuenta → "Usar esta cuenta" → "Ingresar".

> ⚠️ Son cuentas **públicas** compartidas: no ingreses datos personales, médicos ni reales. Todos los datos son sintéticos y la base se restablece en cada reinicio del servicio.

Límites de seguridad de las cuentas demo (aplicados en el backend):
- gestión de usuarios **solo lectura** (no pueden crear, editar, eliminar usuarios ni cambiar roles);
- no pueden cambiar su contraseña;
- no pueden borrar los datos sintéticos de referencia (sí los registros que ellas mismas crean);
- ven enmascarados los correos de cuentas no públicas y las IP del registro de auditoría.

Las cuentas se crean con un *seed* idempotente (`flask bootstrap` o `flask seed-demo-accounts`): si ya existen no se duplican; si fueron alteradas se restauran rol, estado y contraseña. Se desactivan con `DEMO_ACCOUNTS=0`. Las cuentas privadas de administración (`ADMIN_PASSWORD`, etc.) son distintas, se generan en Render y **nunca** se muestran ni se publican.

## Funcionalidades
- Login, registro (rol operador), logout y cambio de contraseña.
- Roles en el backend: **Administrador**, **Doctor/Especialista**, **Operador**.
- CRUD de astronautas, misiones, mediciones de signos vitales, alertas y usuarios.
- Motor de alertas explicable (umbrales AHA, ACC/AHA 2017, OMS, CDC + línea base personal) con alertas persistidas y revisión médica.
- Dashboard con gráficos, centro de riesgos (5 peligros del HRP de la NASA), datos reales NASA OSDR (OSD-575, OSD-569), reportes CSV y auditoría.
- Seguridad: hash scrypt, CSRF, validación, cabeceras de seguridad, cookies seguras.

## Stack
Flask 3.1 · Flask-SQLAlchemy · Flask-Login · Flask-WTF · SQLite · Gunicorn · pytest (101 pruebas).

## Inicio rápido
```bash
pip install -r requirements.txt
flask --app wsgi init-db
flask --app wsgi create-user --email admin@ejemplo.com --name "Admin" --role admin
flask --app wsgi seed-demo
flask --app wsgi seed-demo-accounts   # cuentas públicas de demostración (idempotente)
flask --app wsgi run
python -m pytest -v
```

## Documentación
`docs/academic/`: PROJECT_OVERVIEW, CHALLENGE_DESCRIPTION, SYSTEM_ARCHITECTURE, DATABASE_DESIGN (+ `schema.sql`), USER_MANUAL, TEST_REPORT, DEPLOYMENT_GUIDE, NASA_REFERENCES, AUDIT_REPORT y `evidence/`.

## Equipo NYXARA NOVA
Etner Therry Rios Vasquez · Jeanfranco Alfredo Ibarra Kocfú · Darlin Saldaña Pinedo · Máximo Fabrizzio Espinoza Peche
