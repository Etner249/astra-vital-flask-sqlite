# ASTRA VITAL — Informe de pruebas

Fecha de ejecución: 2026-11-16 12:42 (UTC-5). Salidas originales en `tests/`.

| Conjunto | Herramienta | Resultado | Archivo de salida |
|---|---|---|---|
| Backend Flask + SQLite | pytest 9.1.1 | **136 aprobadas, 0 fallidas** (57,9 s) | `tests/pytest-output.txt`, `tests/pytest-results.xml` |
| Motor de reglas original (JS) | Node.js `tests/engine.test.js` (repo `astra-vital`) | **10/10 aprobadas** | `tests/engine-tests-output.txt` |
| E2E frontend + API, 3 roles | Playwright + Chrome `tests/e2e_academic.py` | **84/84 verificaciones**, 0 errores JS | `tests/playwright-e2e-output.txt` |

## pytest por archivo

| Archivo | Pruebas |
|---|---|
| tests/test_api.py | 34 |
| tests/test_auth.py | 10 |
| tests/test_authorization.py | 51 |
| tests/test_crud.py | 17 |
| tests/test_demo_accounts.py | 11 |
| tests/test_engine.py | 6 |
| tests/test_security.py | 7 |
| **Total** | **136** |

Cada prueba usa una base SQLite en archivo temporal con `PRAGMA foreign_keys=ON`.

## Advertencias

29 `DeprecationWarning` de WTForms 3.3 ("Passing SelectField choices as tuples is deprecated… will be removed in wtforms 3.4"). No afectan el resultado; deben corregirse antes de actualizar a WTForms 3.4.

## Observación de ejecución

Si en la misma terminal se exportan `CORS_ORIGINS` o `DATABASE_PATH` (p. ej. para levantar un servidor local), 25 pruebas de API fallan porque heredan esa configuración. Ejecutar con la configuración por defecto:

```bash
env -u CORS_ORIGINS -u DATABASE_PATH python -m pytest -v
```

## Cómo reproducir

```bash
pip install -r requirements.txt
python -m pytest -v                              # backend
node tests/engine.test.js                        # repo astra-vital
AV_API_BASE=http://127.0.0.1:5056/api/v1 python3 build.py
python3 tests/e2e_academic.py http://127.0.0.1:8080/astra-vital/ shots/
```

Las pruebas verifican el software, no constituyen validación clínica.
