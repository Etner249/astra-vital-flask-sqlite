# Technical Audit of the Original ASTRA VITAL (NASA Space Apps 2026 edition)

Audited source: https://github.com/Etner249/astra-vital (commit `8df773b`, 2026-11-15). The original repository is **not modified** by the academic edition; the Flask version lives in a separate repository (`astra-vital-flask-sqlite`).

## 1. Current architecture
| Aspect | Original edition |
|---|---|
| Type | Single-page static web app (one self-contained `index.html` built by `build.py`) |
| Languages | HTML5, CSS3, vanilla JavaScript, inline SVG |
| Backend | None |
| Persistence | Browser `localStorage` (one browser, one user) |
| Users / roles | None (single fictional crew member) |
| Hosting | GitHub Pages (static) |
| Tests | 10 Node unit tests (`tests/engine.test.js`), 27 Playwright end-to-end checks (`tests/e2e.py`) |

## 2. Modules found
| Module (file) | Status | Reusable in Flask edition |
|---|---|---|
| Health Intelligence Engine (`src/engine.js`) — quality, missing data, documented references, personal baseline (≥2 SD), 7-day trend, consolidation | Implemented | **Yes — ported to Python** (`app/engine.py`) with the same thresholds and sources |
| Mission Dashboard, Log, Interactive Body, Alerts, Risk Center, NASA Data, Profile, Sync & Reports, Ground Console, About (`src/app.js`) | Implemented | Dashboard, alerts, risk center, NASA data, reports re-implemented server-side |
| Visual identity (`src/styles.css`, `assets/brand/*.svg`) | Implemented | **Yes — reused** (palette, typography, components, original symbol) |
| NASA OSDR subset (`data/osdr_i4_subset.csv/json`, OSD-575 + OSD-569) | Real data | **Yes — copied unchanged** |
| Five hazards content (RIDGE) | Implemented | **Yes** |
| Offline sync queue / ground console | **Simulated** inside the browser (two local stores) | Not carried over: the Flask edition has a real server and database, so sync simulation is not needed |
| Synthetic demo vitals (seeded generator) | Synthetic | Re-implemented as a seed command; rows flagged `is_synthetic` |

## 3. Implemented vs simulated (original)
- Implemented: all UI modules, rule engine, validation, local persistence, exports.
- Simulated: Earth link (AOS/LOS), ground store and synchronization; crew vital signs (synthetic).
- Real data: Inspiration4 pre/post-flight clinical lab values (n = 4, 3-day mission) — not in-flight vitals.

## 4. Gaps against the course requirements (Flask + SQLite)
| Requirement | Original | Action in academic edition |
|---|---|---|
| Python Flask backend | ✗ | Flask 3 app factory, blueprints |
| SQLite + ORM | ✗ (localStorage) | SQLite via Flask-SQLAlchemy, 6 tables, FKs, indexes, constraints |
| Users, login, roles | ✗ | Flask-Login, 3 roles enforced in the backend |
| CSRF, hashing | n/a | Flask-WTF CSRF, Werkzeug password hashes |
| Full CRUD | Partial (measurements only) | CRUD for users, astronauts, missions, measurements, alerts |
| pytest | ✗ (Node + Playwright) | pytest + Flask test client |
| Render deployment | ✗ (GitHub Pages) | `render.yaml`, Gunicorn |

## 5. Risks identified
- SQLite on Render's free instance is **not persistent** (no persistent disks on free instances; the filesystem is reset on restart/redeploy). The team chose the free plan; the database is re-initialized with demo data on each start and this limitation is documented.
- Clinical thresholds must stay educational; the engine keeps the original warnings ("not a medical device").
