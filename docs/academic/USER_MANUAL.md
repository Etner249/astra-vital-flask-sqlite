# Manual de usuario

Aplicación: https://astra-vital-academic.onrender.com (la primera carga puede tardar hasta ~50 s si la instancia gratuita estaba suspendida).

## 1. Acceso
- **Iniciar sesión:** correo y contraseña en `/login`. Los mensajes de error son genéricos (no revelan si el correo existe).
- **Crear cuenta:** enlace "Create one". Toda cuenta nueva recibe el rol **Operador**; solo un Administrador puede cambiar roles.
- **Cerrar sesión:** botón "Sign out" del menú (envía un POST protegido con CSRF).
- **Cambiar contraseña:** menú "Settings" (mínimo 10 caracteres, letras y números).
- Las cuentas iniciales de Render se crean con contraseñas generadas por Render; el propietario las consulta en Render → Environment.

## 2. Roles y permisos
| Acción | Administrador | Doctor/Especialista | Operador |
|---|:-:|:-:|:-:|
| Ver dashboard, astronautas, mediciones, alertas, misiones, riesgos, datos NASA | ✔ | ✔ | ✔ |
| Registrar mediciones | ✔ | ✔ | ✔ |
| Editar mediciones | ✔ | ✔ | ✘ |
| Eliminar mediciones | ✔ | ✘ | ✘ |
| Revisar / cambiar estado de alertas, regenerar alertas | ✔ | ✔ | ✘ |
| Crear, editar, eliminar astronautas y misiones | ✔ | ✘ | ✘ |
| Reportes y exportación CSV | ✔ | ✔ | ✘ |
| Gestionar usuarios y roles | ✔ | ✘ | ✘ |
| Ver auditoría | ✔ | ✘ | ✘ |

Si un rol intenta acceder a una función no permitida (incluso escribiendo la URL), el servidor responde **403 – Acceso denegado**.

## 3. Módulos
- **Dashboard:** totales (astronautas, mediciones, alertas abiertas y prioritarias), estado por astronauta y gráfico de evolución de signos vitales.
- **Astronautas:** listado con búsqueda; ficha con misión, últimas mediciones, gráficos y alertas; crear/editar/eliminar (admin). Si el astronauta tiene alertas prioritarias abiertas, la eliminación pide marcar una confirmación explícita.
- **Misiones:** listado y formulario (admin). No se puede eliminar una misión con astronautas asignados.
- **Mediciones:** registrar FC, PA sistólica/diastólica, SpO2, temperatura, FR, fecha/hora y observaciones. Filtrar por astronauta y rango de fechas; paginación. Al guardar, el motor genera alertas automáticamente.
- **Alertas:** filtrar por estado y nivel (informativa, seguimiento, prioritaria). Cada alerta muestra *qué cambió*, *por qué importa*, *qué hacer*, *cuándo contactar al médico* y la *fuente*. Doctor/Admin pueden marcarla como reconocida o resuelta con notas.
- **Centro de riesgos:** los 5 peligros del HRP de la NASA y su relación con los indicadores.
- **Datos NASA:** subconjunto real de OSD-575 / OSD-569 (Inspiration4), con aclaración de que son análisis de laboratorio pre/post vuelo.
- **Reportes:** resumen y exportación CSV de mediciones y alertas.
- **Usuarios:** crear, editar rol/estado, eliminar (admin). No se puede eliminar la propia cuenta ni al último administrador.
- **Auditoría:** registro de inicios de sesión y operaciones de escritura.

## 4. Interpretación de niveles de alerta
| Nivel | Significado | Ejemplo |
|---|---|---|
| Seguimiento | Repetir medición, vigilar e informar en la próxima ventana de comunicación | FC fuera de 60–100 lpm, SpO2 90–94 %, PA estadio 2 (≥140/90) o baja (<90/60), FR fuera de 12–20, desviación ≥2 DE de la línea base personal |
| Prioritaria | Contactar al médico de vuelo lo antes posible | SpO2 < 90 %, PA > 180 y/o > 120, temperatura ≥ 38,0 °C |

El nivel *informativa* existe en el modelo de datos (y en el estado global "sin novedades"), pero las reglas actuales solo generan alertas de seguimiento o prioritarias.

*Prototipo educativo: no sustituye la evaluación médica.*
