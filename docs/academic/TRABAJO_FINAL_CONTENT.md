# Introducción

Las misiones espaciales de larga duración —estancias de seis meses o más en la Estación Espacial Internacional y, en el futuro, viajes a la Luna y Marte— exponen a la tripulación a radiación, aislamiento, microgravedad y ambientes cerrados. Con la distancia, la comunicación con el equipo médico en Tierra se retrasa o se interrumpe, y el propio astronauta debe vigilar su salud y decidir cuándo pedir ayuda.

ASTRA VITAL nació como respuesta del equipo **NYXARA NOVA** al reto *Create Health Monitoring Software for Astronauts on Space Missions* del **NASA Space Apps Challenge 2026** (evento local de Trujillo, Perú). El proyecto original, una aplicación web estática con motor de reglas en JavaScript, fue presentado oficialmente a evaluación el 15 de noviembre de 2026.

Este informe documenta la **edición académica** de ASTRA VITAL: una reconstrucción posterior del sistema como aplicación web completa con **Python Flask** y **SQLite**, que añade base de datos relacional, autenticación, roles, operaciones CRUD, pruebas automatizadas y despliegue en la nube. La versión Flask **no** es la que se presentó a la NASA; reutiliza su identidad visual, su motor de reglas (portado a Python) y sus fuentes científicas.

El sistema es un **prototipo educativo**: no es un dispositivo médico, no diagnostica y sus astronautas y mediciones de demostración son sintéticos.

# Descripción del desafío NASA

{{include:CHALLENGE_DESCRIPTION.md|skip=Problema identificado,Solución propuesta (edición académica)}}

# Problema identificado

En una misión larga, el astronauta y el personal de apoyo necesitan:

- **Registrar** signos vitales de forma ordenada y trazable (quién midió, cuándo, con qué valores).
- **Interpretar** si un valor es preocupante, tanto frente a referencias clínicas documentadas como frente a la propia línea base del astronauta (un valor "normal" para la población puede ser anormal para una persona concreta).
- **Saber qué hacer** y **cuándo contactar** al médico de vuelo, con explicaciones claras y no solo con un color.
- **Conservar el historial** de mediciones y alertas, con revisión médica y auditoría.
- **Controlar el acceso**: no todos los usuarios deben poder modificar o borrar datos clínicos.

La versión original de ASTRA VITAL resolvía la interpretación en el navegador con datos locales, pero no tenía usuarios, roles ni base de datos compartida. La edición académica cubre esas carencias.

# Solución propuesta

ASTRA VITAL Academic Edition es una aplicación web multiusuario:

1. El personal inicia sesión con su rol (**Administrador**, **Doctor/Especialista** u **Operador**).
2. Se registran misiones, astronautas y mediciones (frecuencia cardiaca, presión arterial sistólica y diastólica, SpO2, temperatura, frecuencia respiratoria, fecha/hora y observaciones).
3. Al guardar una medición, un **motor de reglas explicable** la compara con umbrales documentados (AHA, ACC/AHA 2017, OMS, CDC) y con la **línea base personal** (desviación ≥ 2 DE sobre las primeras 7 mediciones), y genera **alertas persistidas** en SQLite con: qué cambió, por qué importa, qué hacer, cuándo contactar y fuente.
4. Doctor y Administrador revisan las alertas (reconocida / resuelta) con notas.
5. Un **centro de riesgos** relaciona los indicadores con los 5 peligros del Programa de Investigación Humana (HRP) de la NASA, y un módulo de **datos NASA** muestra datos reales del repositorio OSDR (Inspiration4: OSD-575 y OSD-569).
6. Todas las operaciones de escritura y los inicios de sesión quedan en un **registro de auditoría**.

# Objetivos

## Objetivo general

Desarrollar una aplicación web con Python Flask y SQLite que permita registrar astronautas, misiones y signos vitales, generar y gestionar alertas explicables de salud y controlar el acceso por roles, conservando la identidad y el fundamento científico de ASTRA VITAL.

## Objetivos específicos

1. Diseñar una base de datos SQLite normalizada de seis tablas con claves primarias y foráneas, restricciones CHECK/UNIQUE e índices.
2. Implementar operaciones CRUD completas para usuarios, astronautas, misiones, mediciones y alertas.
3. Implementar registro, inicio y cierre de sesión, y autorización por roles verificada en el backend.
4. Portar el motor de reglas de JavaScript a Python y persistir sus alertas.
5. Aplicar medidas de seguridad: contraseñas con hash, CSRF, validación, cookies seguras, cabeceras de seguridad y auditoría.
6. Verificar el sistema con pruebas automatizadas (pytest) y desplegarlo públicamente en Render.

# Arquitectura del sistema

{{include:SYSTEM_ARCHITECTURE.md|skip=Tecnologías}}

# Tecnologías utilizadas

| Capa | Tecnología | Uso |
|---|---|---|
| Lenguaje | Python 3 | Backend, motor de reglas, pruebas |
| Framework web | Flask 3.1.3 | App factory, blueprints, plantillas Jinja2 |
| ORM | Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.1.8 | Modelos y consultas |
| Base de datos | SQLite 3 | Archivo único, FK y WAL activados |
| Autenticación | Flask-Login 0.6.3 + Werkzeug (scrypt) | Sesiones y hash de contraseñas |
| Formularios | Flask-WTF 1.3.0 / WTForms 3.3.2 / email-validator | Validación y CSRF |
| Servidor | Gunicorn 27.0.1 | Servidor WSGI en producción |
| Pruebas | pytest 9.1.1 | 90 pruebas automatizadas |
| Frontend | HTML5, CSS3, JavaScript | Interfaz y gráficos SVG propios, sin librerías externas |
| Control de versiones | Git + GitHub | Repositorio público |
| Despliegue | Render (Blueprint `render.yaml`) | Hosting del servicio web |

# Diseño de base de datos

{{include:DATABASE_DESIGN.md}}

# Gestión de usuarios y roles

El control de acceso se define en `app/decorators.py` mediante una **matriz de permisos**. Cada ruta protegida usa el decorador `permission_required("permiso")`, que devuelve **403** si el rol del usuario no tiene ese permiso; la interfaz solo oculta botones como comodidad, pero la decisión se toma en el servidor.

| Permiso | Administrador | Doctor/Especialista | Operador |
|---|:-:|:-:|:-:|
| Ver módulos (dashboard, astronautas, mediciones, alertas, misiones, riesgos, datos NASA) | Sí | Sí | Sí |
| Registrar mediciones | Sí | Sí | Sí |
| Editar mediciones | Sí | Sí | No |
| Eliminar mediciones | Sí | No | No |
| Gestionar alertas (revisar, regenerar) | Sí | Sí | No |
| Gestionar astronautas y misiones | Sí | No | No |
| Reportes y CSV | Sí | Sí | No |
| Gestionar usuarios y roles | Sí | No | No |
| Auditoría | Sí | No | No |

Reglas adicionales:

- El **registro público** crea siempre cuentas de **Operador**; solo un Administrador asigna otros roles.
- El administrador inicial no está en el código: se crea con `flask create-user` (la contraseña se pide por consola) o con `flask bootstrap` a partir de variables de entorno que en Render se generan automáticamente.
- Un administrador no puede eliminarse a sí mismo, quitarse el rol ni eliminar al último administrador.
- Las cuentas pueden desactivarse (`is_active_account`); una cuenta inactiva no puede iniciar sesión.
- Las contraseñas se guardan con hash scrypt con sal (Werkzeug) y deben tener al menos 10 caracteres con letras y números.

# Operaciones CRUD

| Entidad | Crear | Leer | Actualizar | Eliminar |
|---|---|---|---|---|
| Usuarios | Admin (formulario) y registro público (operador) | Listado (admin) | Nombre, rol, estado (admin); contraseña propia (todos) | Admin, con protecciones |
| Astronautas | Admin | Listado con búsqueda y ficha detallada (todos) | Admin | Admin; cascada a mediciones y alertas; confirmación si hay alertas prioritarias abiertas |
| Misiones | Admin | Listado (todos) | Admin | Admin; bloqueado si tiene astronautas asignados |
| Mediciones | Todos los roles | Listado con filtros por astronauta y fechas, paginado | Admin y Doctor; regenera alertas | Solo Admin; conserva alertas ya revisadas |
| Alertas | Automática (motor de reglas) | Listado con filtros por estado y nivel; detalle con explicación | Estado y notas de revisión (Admin, Doctor) | Se eliminan con su astronauta o al regenerar alertas abiertas |

Cada operación de escritura pasa por un formulario con token CSRF, validación en WTForms y restricciones en SQLite, y se registra en `audit_logs`.

# Descripción de módulos

| Módulo | Ruta | Descripción |
|---|---|---|
| Autenticación | `/login`, `/register`, `/logout`, `/settings` | Inicio y cierre de sesión, registro de operadores, cambio de contraseña |
| Dashboard | `/dashboard` | Totales, alertas abiertas y prioritarias, estado por astronauta, gráfico de evolución |
| Astronautas | `/astronauts` | CRUD, búsqueda y ficha con mediciones, gráficos y alertas |
| Misiones | `/missions` | CRUD de misiones (ficticias en la demo) |
| Mediciones | `/measurements` | Registro de signos vitales, filtros por astronauta y fechas, historial |
| Alertas | `/alerts` | Alertas explicables persistidas, revisión médica, regeneración |
| Centro de riesgos | `/risks` | Los 5 peligros del HRP de la NASA y su relación con los indicadores |
| Datos NASA | `/nasa-data` | Subconjunto real de OSDR OSD-575 / OSD-569 (Inspiration4) |
| Reportes | `/reports` | Resumen y exportación CSV |
| Usuarios | `/users` | Gestión de cuentas y roles |
| Auditoría | `/audit` | Registro de accesos y cambios |
| Acerca de | `/about` | Origen del proyecto, alcance y limitaciones |

### Motor de alertas

| Indicador | Seguimiento | Prioritaria | Fuente |
|---|---|---|---|
| Frecuencia cardiaca | Fuera de 60–100 lpm | — | AHA |
| Presión arterial | ≥ 140/90 (estadio 2) o < 90/60 | > 180 y/o > 120 | ACC/AHA 2017 |
| SpO2 | 90–94 % | < 90 % | OMS |
| Temperatura | — | ≥ 38,0 °C | CDC |
| Frecuencia respiratoria | Fuera de 12–20 rpm | — | Referencia clínica estándar |
| Cualquiera (línea base) | Desviación ≥ 2 DE frente a las primeras 7 mediciones | — | Convención del motor |

Los hallazgos de un mismo indicador se consolidan en una sola alerta, con la regla más grave como principal y el resto como evidencia de apoyo.

# Capturas reales de la aplicación

Todas las capturas se tomaron de la aplicación real en ejecución (navegador Chrome automatizado con Playwright sobre el servidor Flask local con datos sintéticos, y del navegador sobre el despliegue en Render). Los datos de astronautas y mediciones son sintéticos.

{{fig:01_login.png|Pantalla de inicio de sesión}}
{{fig:02_dashboard_admin.png|Dashboard del Administrador}}
{{fig:03_astronauts_list.png|Listado de astronautas}}
{{fig:04a_astronaut_create_form.png|Crear astronauta: formulario}}
{{fig:04b_astronaut_created.png|Crear astronauta: registro guardado}}
{{fig:05a_astronaut_edit_form.png|Editar astronauta: formulario}}
{{fig:05b_astronaut_updated.png|Editar astronauta: cambios guardados}}
{{fig:06a_astronaut_delete_confirm.png|Eliminar astronauta: confirmación}}
{{fig:06b_astronaut_deleted.png|Eliminar astronauta: resultado}}
{{fig:07_measurements_management.png|Gestión de mediciones}}
{{fig:08a_measurement_create_form.png|Registrar medición: formulario}}
{{fig:08b_measurement_saved_with_alerts.png|Medición guardada con alertas generadas}}
{{fig:09_measurement_history_filtered.png|Historial de mediciones filtrado por astronauta y fechas}}
{{fig:10a_alerts.png|Listado de alertas}}
{{fig:10b_alert_detail_review.png|Detalle y revisión de una alerta}}
{{fig:11_users_and_permissions.png|Gestión de usuarios y roles}}
{{fig:12_doctor_dashboard.png|Dashboard con rol Doctor/Especialista}}
{{fig:12_doctor_users_forbidden_403.png|Doctor intenta acceder a Usuarios: 403}}
{{fig:12_operator_dashboard.png|Dashboard con rol Operador}}
{{fig:12_operator_users_forbidden_403.png|Operador intenta acceder a Usuarios: 403}}
{{fig:16_missions.png|Misiones}}
{{fig:17_reports.png|Reportes y exportación CSV}}
{{fig:18_risk_center.png|Centro de riesgos (5 peligros HRP)}}
{{fig:19_nasa_data.png|Datos NASA OSDR}}
{{fig:20_audit_log.png|Registro de auditoría}}
{{fig:21_mobile_dashboard.png|Vista móvil del dashboard|narrow}}

# Pruebas automatizadas y resultados

{{include:TEST_REPORT.md}}

{{fig:13_pytest_results.png|Resultado real de la ejecución de pytest: 90 pruebas aprobadas|tall}}

# Despliegue en Render

{{include:DEPLOYMENT_GUIDE.md|skip=URLs reales}}

{{fig:14a_render_deployed_login.jpg|Aplicación desplegada en Render (astra-vital-academic.onrender.com/login)|half}}
{{fig:14b_render_logs_first_deploy.jpg|Logs del primer despliegue: creación de usuarios y datos de demostración|half}}
{{fig:14c_render_redeploy_db_recreated.jpg|Nuevo despliegue: la base SQLite se crea desde cero|half}}
{{fig:14d_render_restart_db_recreated.jpg|Reinicio del servicio: la base SQLite se crea desde cero|half}}
{{fig:15_render_after_login.png|Aplicación desplegada después de iniciar sesión|optional}}

# Enlace al repositorio GitHub

- **Repositorio académico (Flask + SQLite):** https://github.com/Etner249/astra-vital-flask-sqlite
- **Proyecto original presentado a NASA Space Apps 2026 (no modificado):** https://github.com/Etner249/astra-vital

El repositorio académico no contiene contraseñas, claves secretas ni archivos `.env` ni bases de datos: `.gitignore` excluye `instance/`, `*.db` y `.env`, y las credenciales de Render se generan en la plataforma (`generateValue`).

| Ruta | Contenido |
|---|---|
| `app/` | Código de la aplicación Flask |
| `tests/` | Pruebas pytest |
| `docs/academic/` | Documentación académica, `schema.sql` y evidencias |
| `render.yaml`, `gunicorn.conf.py`, `Procfile` | Configuración de despliegue |
| `requirements.txt`, `.env.example` | Dependencias y variables de ejemplo |

# Enlace a la aplicación desplegada

- **Aplicación:** https://astra-vital-academic.onrender.com
- **Servicio:** `astra-vital-academic`, Render, plan gratuito, región Oregon.
- La primera carga puede tardar hasta ~50 segundos si la instancia gratuita estaba suspendida por inactividad.
- La base de datos se reinicia en cada reinicio o despliegue y siempre contiene los datos sintéticos de demostración (ver capítulo de despliegue).
- Las cuentas iniciales (`admin@nyxara.example`, `doctor@nyxara.example`, `operator@nyxara.example`) usan contraseñas generadas por Render, que solo conoce el propietario de la cuenta; para revisar la aplicación se puede crear una cuenta de Operador desde "Create one".

# Certificado NASA Space Apps Challenge 2026

{{cert}}

# Conclusiones

1. Se construyó una aplicación web funcional con **Python Flask y SQLite** que cumple los requisitos del curso: seis tablas relacionadas con claves foráneas, restricciones e índices; CRUD completo; autenticación; y tres roles con permisos verificados en el backend.
2. El motor de reglas de ASTRA VITAL se portó de JavaScript a Python y sus alertas ahora se **persisten** con explicación, acción sugerida, criterio de contacto y fuente, y pueden ser revisadas por personal médico.
3. La seguridad se abordó en varias capas: hash scrypt, CSRF en todas las acciones, validación en formularios y en la base de datos, cookies seguras, cabeceras de seguridad, redirecciones seguras y auditoría.
4. Las **90 pruebas automatizadas** pasan sin fallos y cubren autenticación, autorización, CRUD, motor de alertas y seguridad.
5. El sistema está desplegado públicamente en Render. Se verificó que en el **plan gratuito SQLite no persiste**: tras un nuevo despliegue y tras un reinicio la base se crea desde cero. Para uso real se requeriría un disco persistente (plan de pago) o una base de datos gestionada.
6. El trabajo muestra cómo una idea creada en un hackatón internacional puede evolucionar hacia una aplicación más robusta, manteniendo una base científica (NASA HRP, NASA OSDR, guías clínicas) y aclarando sus límites: es un prototipo educativo y no un dispositivo médico.

**Trabajo futuro:** persistencia real (disco o PostgreSQL), integración con sensores, notificaciones, pruebas de interfaz automatizadas y validación de umbrales con profesionales de la salud.

# Referencias bibliográficas

{{include:NASA_REFERENCES.md}}
