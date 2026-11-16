# Guía de despliegue

## URLs reales
- Repositorio académico: https://github.com/Etner249/astra-vital-flask-sqlite
- Aplicación en Render: https://astra-vital-academic.onrender.com
- Servicio Render: `astra-vital-academic` (Python 3, región Oregon, plan **Free**), creado desde el Blueprint `render.yaml` el 16/11/2026 (primer deploy en vivo 10:58, commit `e93d6e7`).

## Ejecución local
```bash
git clone https://github.com/Etner249/astra-vital-flask-sqlite.git
cd astra-vital-flask-sqlite
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app wsgi init-db
flask --app wsgi create-user --email admin@ejemplo.com --name "Admin" --role admin   # pide la contraseña sin mostrarla
flask --app wsgi seed-demo        # opcional: datos sintéticos
flask --app wsgi run              # http://127.0.0.1:5000
python -m pytest -v               # pruebas
```
Variables (ver `.env.example`): `SECRET_KEY`, `DATABASE_PATH`, `FLASK_ENV_MODE`. El archivo `.env` y la base `instance/*.db` están en `.gitignore`.

## Despliegue en Render (Blueprint)
1. Render → **New → Blueprint** → *Public Git Repository*: `https://github.com/Etner249/astra-vital-flask-sqlite`.
2. Render lee `render.yaml`:
   - build: `pip install -r requirements.txt`
   - start: `flask --app wsgi bootstrap && gunicorn -c gunicorn.conf.py wsgi:app`
   - health check: `/login`
   - `SECRET_KEY`, `ADMIN_PASSWORD`, `DOCTOR_PASSWORD`, `OPERATOR_PASSWORD`: `generateValue: true` (Render genera valores aleatorios; **no están en GitHub**).
3. Las contraseñas generadas se consultan en Render → servicio → **Environment** (solo el propietario de la cuenta).
4. `bootstrap` crea las tablas, crea los 3 usuarios iniciales si no existen y carga los datos sintéticos (`SEED_DEMO=1`).

## Persistencia de SQLite en Render (resultado verificado)
El plan gratuito de Render usa un sistema de archivos **efímero** y no admite discos persistentes. Por decisión del equipo se usó el plan gratuito, por lo tanto:

| Evento | Comportamiento observado | Evidencia |
|---|---|---|
| Primer deploy (10:58) | Base creada desde cero: "Created admin/doctor/operator", "Seeded 83 synthetic measurements" | Logs de Render, `evidence/14b_render_logs_first_deploy.jpg` |
| Nuevo deploy manual (commit `ae950ad`, 11:03–11:04) | Log: "No SQLite database at /opt/render/project/src/instance/astra_vital.db: creating a new one" · "Database contents: 0 users, 0 astronauts" → se recrean usuarios y datos | `evidence/14c_render_redeploy_db_recreated.jpg` |
| Reinicio del servicio ("Restart service", 11:05–11:06, instancia `76v2v`) | Mismo resultado: no existe la base anterior, se crea una nueva con 0 usuarios y se vuelve a sembrar | `evidence/14d_render_restart_db_recreated.jpg` |

**Consecuencia:** cualquier dato creado por los usuarios en la instancia gratuita se pierde al reiniciar, al redesplegar o cuando Render suspende la instancia por inactividad (~15 min); la app vuelve a su estado de demostración. Esto es aceptable para una demo académica, no para uso real.

**Para persistencia real:** instancia de pago + Persistent Disk (bloque comentado en `render.yaml`):
```yaml
disk:
  name: astra-data
  mountPath: /var/data
  sizeGB: 1
# y DATABASE_PATH=/var/data/astra_vital.db
```
Con disco montado, `bootstrap` detecta la base existente ("Existing SQLite database found…") y no duplica usuarios ni datos (comprobado localmente: segunda ejecución → "1 users, 4 astronauts", "Seeded 0").

## Verificación (16/11/2026)
1. `GET /login` en https://astra-vital-academic.onrender.com responde 200 (health check de Render cada 5 s y navegador) — `evidence/14a_render_deployed_login.jpg`.
2. Primer deploy, redeploy y reinicio muestran en los logs que la base SQLite se crea desde cero cada vez (tabla anterior). **Conclusión: en el plan gratuito los datos no persisten; la aplicación siempre arranca en estado de demostración.**
3. Inicio de sesión en producción: realizado por el propietario de la cuenta con la contraseña generada por Render (nunca escrita en el repositorio) — `evidence/15_render_after_login.png`.
