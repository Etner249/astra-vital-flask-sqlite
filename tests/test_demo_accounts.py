"""Public demo accounts (NASA Evaluator Access): seeding, login, role permissions and safety limits."""
import os
import pytest
from app.demo import DEMO_ACCOUNTS, ensure_demo_accounts
from app.extensions import db
from app.models import User, Astronaut, Mission, HealthMeasurement
from datetime import date, datetime

ACC = {a["role"]: a for a in DEMO_ACCOUNTS}


@pytest.fixture
def demo_app(app):
    with app.app_context():
        ensure_demo_accounts()
        m = Mission(code="AV-SYN", name="Synthetic", environment="station", start_date=date(2026, 1, 1),
                    duration_days=30, status="active", is_synthetic=True)
        db.session.add(m)
        db.session.flush()
        a = Astronaut(code="AV-SYN-01", full_name="Synthetic One", mission_id=m.id, is_synthetic=True)
        db.session.add(a)
        db.session.flush()
        db.session.add(HealthMeasurement(astronaut_id=a.id, measured_at=datetime(2026, 1, 2, 8), heart_rate=70,
                                         source="synthetic_demo", is_synthetic=True))
        db.session.commit()
    return app


def demo_login(client, role):
    return client.post("/login", data={"email": ACC[role]["email"], "password": ACC[role]["password"]}, follow_redirects=True)


def test_seed_is_idempotent_and_repairs(app):
    with app.app_context():
        assert ensure_demo_accounts() == (3, 0)
        assert ensure_demo_accounts() == (0, 0)
        assert User.query.filter_by(is_demo=True).count() == 3
        # tampered account is restored (role, status, password) without creating duplicates
        u = User.query.filter_by(email=ACC["doctor"]["email"]).first()
        u.role, u.is_active_account = "operator", False
        u.set_password("SomethingElse123")
        db.session.commit()
        assert ensure_demo_accounts() == (0, 1)
        u = User.query.filter_by(email=ACC["doctor"]["email"]).first()
        assert u.role == "doctor" and u.is_active_account and u.check_password(ACC["doctor"]["password"])
        assert User.query.filter(User.email.in_([a["email"] for a in DEMO_ACCOUNTS])).count() == 3
        assert all(u.password_hash != a["password"] for a, u in
                   ((a, User.query.filter_by(email=a["email"]).first()) for a in DEMO_ACCOUNTS))


@pytest.mark.parametrize("role", ["admin", "doctor", "operator"])
def test_each_demo_account_logs_in_with_its_role(demo_app, role):
    c = demo_app.test_client()
    r = demo_login(c, role)
    assert r.status_code == 200 and b"PUBLIC DEMO ACCOUNT" in r.data
    expected = {"admin": 200, "doctor": 403, "operator": 403}[role]
    assert c.get("/audit").status_code == expected
    assert c.get("/reports").status_code == (403 if role == "operator" else 200)
    assert c.get("/astronauts/new").status_code == (200 if role == "admin" else 403)
    assert c.get("/measurements/new").status_code == 200


def test_login_page_shows_demo_credentials_but_no_secrets(demo_app, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "Very-Secret-Env-Value-99")
    html = demo_app.test_client().get("/login").get_data(as_text=True)
    assert "NASA EVALUATOR ACCESS" in html and "Credenciales de demostración" in html
    for a in DEMO_ACCOUNTS:
        assert a["email"] in html and a["password"] in html
    assert "Very-Secret-Env-Value-99" not in html and "test-secret" not in html
    assert "no ingreses datos personales" in html


def test_demo_section_can_be_disabled(demo_app):
    demo_app.config["DEMO_ACCOUNTS_ENABLED"] = False
    html = demo_app.test_client().get("/login").get_data(as_text=True)
    assert "NASA EVALUATOR ACCESS" not in html and ACC["admin"]["password"] not in html


def test_demo_admin_user_management_is_read_only(demo_app):
    c = demo_app.test_client()
    demo_login(c, "admin")
    r = c.get("/users")
    assert r.status_code == 200 and "solo lectura".encode() in r.data
    assert b"admin@nyxara.example" not in r.data  # private accounts are masked
    with demo_app.app_context():
        target = User.query.filter_by(email="operator@nyxara.example").first().id
    assert c.get("/users/new").status_code == 403
    assert c.post("/users/new", data={"full_name": "X", "email": "x@nyxara.example", "role": "admin",
                                      "password": "Abcdefgh1234", "is_active_account": "y"}).status_code == 403
    assert c.post(f"/users/{target}/edit", data={"full_name": "X", "email": "operator@nyxara.example", "role": "admin"}).status_code == 403
    assert c.post(f"/users/{target}/delete").status_code == 403
    with demo_app.app_context():
        assert User.query.filter_by(email="x@nyxara.example").first() is None
        assert db.session.get(User, target).role == "operator"


def test_demo_cannot_change_password(demo_app):
    c = demo_app.test_client()
    demo_login(c, "operator")
    r = c.post("/settings", data={"current": ACC["operator"]["password"], "password": "NewPassword123", "confirm": "NewPassword123"})
    assert r.status_code == 403
    with demo_app.app_context():
        assert User.query.filter_by(email=ACC["operator"]["email"]).first().check_password(ACC["operator"]["password"])


def test_demo_admin_cannot_delete_synthetic_baseline_but_can_delete_own_records(demo_app):
    c = demo_app.test_client()
    demo_login(c, "admin")
    with demo_app.app_context():
        a = Astronaut.query.filter_by(code="AV-SYN-01").first()
        aid, mid, msid = a.id, a.mission_id, a.measurements[0].id
    assert c.post(f"/astronauts/{aid}/delete").status_code == 403
    assert c.post(f"/missions/{mid}/delete").status_code == 403
    assert c.post(f"/measurements/{msid}/delete").status_code == 403
    # a record created by the evaluator can be deleted (full CRUD demo)
    r = c.post("/astronauts/new", data={"code": "AV-EVAL-01", "full_name": "Evaluator Test", "status": "active", "mission_id": 0},
               follow_redirects=True)
    assert r.status_code == 200
    with demo_app.app_context():
        new = Astronaut.query.filter_by(code="AV-EVAL-01").first()
        assert new is not None
        new_id = new.id
    assert c.post(f"/astronauts/{new_id}/delete", follow_redirects=True).status_code == 200
    with demo_app.app_context():
        assert db.session.get(Astronaut, new_id) is None
        assert db.session.get(Astronaut, aid) is not None


def test_private_admin_keeps_full_user_management(demo_app):
    c = demo_app.test_client()
    c.post("/login", data={"email": "admin@nyxara.example", "password": "AdminPass2026x"})
    assert c.get("/users/new").status_code == 200
    r = c.get("/users")
    assert b"admin.demo@astravital.example" in r.data and b"admin@nyxara.example" in r.data


def test_audit_masks_ip_for_demo_viewers(demo_app):
    c = demo_app.test_client()
    c.post("/login", data={"email": "nobody@nyxara.example", "password": "wrongpassword1"})
    demo_login(c, "admin")
    html = c.get("/audit").get_data(as_text=True)
    assert "127.0.0.1" not in html and "nobody@nyxara.example" not in html and "oculta" in html
