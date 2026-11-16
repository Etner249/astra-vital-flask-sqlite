# Diseño de la base de datos SQLite

Motor: **SQLite 3** mediante **Flask-SQLAlchemy (SQLAlchemy 2 ORM)**. El esquema se crea de forma reproducible con `flask init-db` / `flask bootstrap` (`db.create_all()`). El DDL real extraído de la base generada está en `schema.sql`. Las claves foráneas se activan en cada conexión con `PRAGMA foreign_keys=ON`.

## Diagrama entidad–relación
```
users (1) ───< health_measurements.recorded_by_id   (SET NULL)
users (1) ───< health_alerts.reviewed_by_id         (SET NULL)
users (1) ───< audit_logs.user_id                   (SET NULL)
missions (1) ───< astronauts.mission_id             (RESTRICT)
astronauts (1) ───< health_measurements.astronaut_id (CASCADE)
astronauts (1) ───< health_alerts.astronaut_id       (CASCADE)
health_measurements (1) ───< health_alerts.measurement_id (SET NULL)
```

## Tablas
### users
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| full_name | VARCHAR(120) | NOT NULL |
| email | VARCHAR(160) | NOT NULL, índice UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL (hash scrypt) |
| role | VARCHAR(20) | NOT NULL, CHECK IN ('admin','doctor','operator') |
| is_active_account | BOOLEAN | NOT NULL |
| last_login_at | DATETIME | |
| created_at, updated_at | DATETIME | NOT NULL |

### missions
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| code | VARCHAR(30) | NOT NULL, UNIQUE |
| name | VARCHAR(120) | NOT NULL |
| environment | VARCHAR(40) | NOT NULL |
| start_date | DATE | NOT NULL |
| duration_days | INTEGER | CHECK 1–1500 |
| status | VARCHAR(20) | CHECK IN ('planned','active','completed') |
| description | TEXT | |
| is_synthetic | BOOLEAN | NOT NULL |
| created_at, updated_at | DATETIME | NOT NULL |

### astronauts
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| code | VARCHAR(30) | NOT NULL, índice UNIQUE |
| full_name | VARCHAR(120) | NOT NULL |
| demo_age | INTEGER | CHECK 18–80 o NULL |
| role_on_board | VARCHAR(60) | |
| mission_id | INTEGER | FK → missions.id ON DELETE RESTRICT, índice |
| status | VARCHAR(20) | CHECK IN ('active','inactive','returned') |
| notes | TEXT | |
| is_synthetic | BOOLEAN | NOT NULL |
| created_at, updated_at | DATETIME | NOT NULL |

### health_measurements
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| astronaut_id | INTEGER | NOT NULL, FK → astronauts.id ON DELETE CASCADE |
| measured_at | DATETIME | NOT NULL; índice compuesto (astronaut_id, measured_at) |
| heart_rate | INTEGER | CHECK 25–230 |
| systolic_bp / diastolic_bp | INTEGER | CHECK 60–260 / 30–160 |
| spo2 | FLOAT | CHECK 50–100 |
| temperature | FLOAT | CHECK 32–43 |
| respiratory_rate | INTEGER | CHECK 4–60 |
| notes | TEXT | |
| source | VARCHAR(40) | 'manual' o 'synthetic_demo' |
| is_synthetic | BOOLEAN | NOT NULL |
| recorded_by_id | INTEGER | FK → users.id ON DELETE SET NULL |
| created_at, updated_at | DATETIME | NOT NULL |

### health_alerts
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| astronaut_id | INTEGER | NOT NULL, FK → astronauts.id ON DELETE CASCADE |
| measurement_id | INTEGER | FK → health_measurements.id ON DELETE SET NULL, índice |
| level | VARCHAR(10) | CHECK IN ('info','followup','priority') |
| metric, rule, title | VARCHAR | NOT NULL |
| what_changed, why, action, contact | TEXT | NOT NULL (explicación completa) |
| source_ref | TEXT | fuente documental |
| status | VARCHAR(15) | CHECK IN ('open','acknowledged','resolved'); índice (status, level) |
| review_notes, reviewed_by_id, reviewed_at | | revisión por doctor/admin |
| created_at, updated_at | DATETIME | NOT NULL |

### audit_logs
| Campo | Tipo | Restricciones |
|---|---|---|
| id | INTEGER | PK |
| created_at | DATETIME | NOT NULL, índice |
| updated_at | DATETIME | NOT NULL |
| user_id | INTEGER | FK → users.id ON DELETE SET NULL |
| action | VARCHAR(20) | login, login_failed, logout, create, update, delete |
| entity, entity_id, details, ip_address | | |

## Eliminación controlada
- **Astronauta:** borra en cascada sus mediciones y alertas; si tiene alertas prioritarias abiertas, exige confirmación explícita.
- **Misión:** no se puede eliminar si tiene astronautas asignados (FK RESTRICT + validación en la ruta).
- **Medición:** elimina sus alertas abiertas; las alertas ya revisadas se conservan (FK SET NULL) como historial.
- **Usuario:** solo un administrador; no puede borrarse a sí mismo ni al último administrador; sus registros históricos conservan la referencia en NULL.

## Datos iniciales
`flask seed-demo` (o `bootstrap` con `SEED_DEMO=1`) crea 2 misiones ficticias, 4 astronautas ficticios (AV-DEMO-01…04) y 21 días de mediciones **sintéticas** (`is_synthetic=1`, `source='synthetic_demo'`), y ejecuta el motor para generar alertas reales sobre esos datos.

## Persistencia y limitaciones de SQLite
- En desarrollo el archivo vive en `instance/astra_vital.db` y persiste entre reinicios.
- SQLite admite un solo escritor a la vez: adecuado para un prototipo académico con pocos usuarios; se usan 2 workers de Gunicorn y modo WAL.
- En Render **plan gratuito** no hay discos persistentes: el archivo se pierde en cada reinicio/redespliegue y se recrea con datos de demostración. Para persistencia real se necesita una instancia de pago con un Persistent Disk montado (p. ej. `/var/data`) y `DATABASE_PATH=/var/data/astra_vital.db`.
