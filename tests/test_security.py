import sqlite3
from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import User


def test_passwords_are_hashed(app, tmp_path):
    with app.app_context():
        u = User.query.filter_by(email="admin@nyxara.example").one()
        assert u.password_hash != "AdminPass2026x" and u.password_hash.startswith(("scrypt:", "pbkdf2:"))
    raw = sqlite3.connect(tmp_path / "test.db").execute("select password_hash from users").fetchall()
    assert all("Pass2026x" not in r[0] for r in raw)


def test_csrf_protection_rejects_forms_without_token(tmp_path):
    app = create_app(TestConfig, SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'csrf.db'}", WTF_CSRF_ENABLED=True)
    with app.app_context():
        db.create_all()
    c = app.test_client()
    r = c.post("/login", data={"email": "x@nyxara.example", "password": "whatever123"})
    assert r.status_code == 400 and b"CSRF" in r.data
    r = c.post("/register", data={"full_name": "Someone", "email": "s@nyxara.example", "password": "Strong12345pw", "confirm": "Strong12345pw"})
    assert r.status_code == 400
    with app.app_context():
        assert User.query.count() == 0


def test_input_validation_measurement(as_role, app):
    c = as_role("operator")
    r = c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 900, "systolic_bp": 80, "diastolic_bp": 95})
    assert b"Number must be between 25 and 230" in r.data and b"Diastolic pressure must be lower than systolic" in r.data
    r = c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00"})
    assert b"Enter at least one vital sign" in r.data
    from app.models import HealthMeasurement
    with app.app_context():
        assert HealthMeasurement.query.count() == 0


def test_database_check_constraint(app):
    """Even bypassing the form, SQLite CHECK constraints reject impossible values."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models import HealthMeasurement
    with app.app_context():
        db.session.add(HealthMeasurement(astronaut_id=1, heart_rate=5))
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_foreign_keys_enforced(app):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models import HealthMeasurement
    with app.app_context():
        db.session.add(HealthMeasurement(astronaut_id=999, heart_rate=70))
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_unauthorized_access_and_security_headers(client):
    r = client.get("/users")
    assert r.status_code == 302
    r = client.get("/login")
    assert r.headers["X-Frame-Options"] == "DENY" and "default-src 'self'" in r.headers["Content-Security-Policy"]


def test_xss_escaped(as_role):
    c = as_role("admin")
    c.post("/astronauts/1/edit", data={"code": "AV-T-01", "full_name": "<script>alert(1)</script>", "mission_id": 0, "status": "active"})
    r = c.get("/astronauts")
    assert b"<script>alert(1)</script>" not in r.data and b"&lt;script&gt;" in r.data
