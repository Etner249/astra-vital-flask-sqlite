# Informe de pruebas

**Herramienta:** pytest 9.1.1 · **Fecha de ejecución:** 16/11/2026 11:20 (UTC−5) · **Comando:** `python -m pytest -v --junitxml=docs/academic/evidence/pytest-results.xml`

## Resultado real
| Total | Aprobadas | Fallidas | Errores | Omitidas | Tiempo |
|---|---|---|---|---|---|
| **101** | **101** | 0 | 0 | 0 | 45,24 s |

21 advertencias de deprecación provienen de WTForms (uso interno de `field_class`), no afectan el resultado. Salida completa: `evidence/pytest-output.txt`; XML JUnit: `evidence/pytest-results.xml`; captura: `evidence/13_pytest_results.png`.

## Entorno de pruebas
- Cada prueba crea una base **SQLite en archivo temporal** (no en memoria), con las mismas restricciones y FK que producción (`PRAGMA foreign_keys=ON`).
- Fixtures (`tests/conftest.py`): un usuario por rol (admin, doctor, operador), una misión y un astronauta de prueba.
- CSRF se desactiva en el cliente de pruebas general y se **activa** explícitamente en la prueba de CSRF.

## Cobertura por módulo
| Archivo | Pruebas | Qué verifica |
|---|---|---|
| `test_auth.py` | 10 | Registro válido/inválido/duplicado, login correcto e incorrecto, cuenta inactiva, logout, redirección a login de rutas protegidas, bloqueo de *open redirect*, cambio de contraseña |
| `test_authorization.py` | 51 | Acceso permitido por rol a cada ruta (admin 16, doctor 11, operador 10), 11 casos de 403 por rol, POST a endpoints de admin, operador no puede editar/eliminar mediciones ni gestionar alertas |
| `test_crud.py` | 17 | Crear/leer/actualizar/eliminar astronautas (código duplicado, cascada, confirmación con alertas prioritarias), mediciones (filtros, regeneración de alertas al editar), alertas persistidas con explicación, regla de línea base, cambio de estado de alerta, misiones con borrado restringido, gestión de usuarios, admin no puede borrarse, exportación CSV |
| `test_engine.py` | 5 | SpO2 < 90 % prioritaria, crisis hipertensiva y estadio 2, valores normales sin alertas, consolidación de una alerta por indicador, estado global |
| `test_demo_accounts.py` | 11 | Seed idempotente y autorreparable de las 3 cuentas demo (sin duplicados), login de cada cuenta con su rol y permisos (3), credenciales visibles en /login sin exponer secretos del entorno, sección desactivable, gestión de usuarios de solo lectura para el admin demo, bloqueo de cambio de contraseña, protección de los datos sintéticos de referencia (y CRUD completo sobre registros propios), administrador privado conserva todos los permisos, IP/correos enmascarados en auditoría |
| `test_security.py` | 7 | Contraseñas con hash, rechazo sin token CSRF, validación de entradas, restricción CHECK en BD, FK forzadas, cabeceras de seguridad, escape XSS |

## Requisitos del curso vs. pruebas
| Requisito | Prueba(s) |
|---|---|
| Registro de usuario | `test_register_*` |
| Login correcto / incorrecto | `test_login_correct`, `test_login_incorrect` |
| Logout | `test_logout` |
| Acceso no autorizado | `test_protected_routes_redirect_to_login`, `test_access_denied_by_role[*]` |
| Permisos por rol | `test_*_authorized[*]`, `test_operator_cannot_*` |
| CRUD astronautas | `test_create/read/update/delete_astronaut*` |
| CRUD mediciones | `test_create/read_and_filter/update/delete_measurement` |
| Generación de alertas | `test_generate_alert_persisted_with_explanation`, `test_baseline_rule_generates_followup` |
| Validación de formularios | `test_input_validation_measurement`, `test_register_invalid_rejected` |
| Protección CSRF | `test_csrf_protection_rejects_forms_without_token` |
| Contraseñas hasheadas | `test_passwords_are_hashed` |

## Pruebas manuales y de navegador
- Se recorrió la aplicación con Playwright/Chrome con los tres roles; las capturas están en `evidence/` (01–21).
- `scripts/verify_demo_accounts.py` prueba en el navegador las tres cuentas públicas usando la propia pantalla de login ("Usar esta cuenta" → "Ingresar"), comprueba el rol mostrado, los códigos HTTP de páginas restringidas y el botón Copiar. Resultado local (16/11/2026): **ALL PASS** — capturas `evidence/22_*`.

## Cómo reproducir
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v
```
