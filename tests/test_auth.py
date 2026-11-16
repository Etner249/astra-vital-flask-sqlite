from app.models import User, AuditLog
from conftest import login


def test_register_valid_creates_operator(client, app):
    r = client.post("/register", data={"full_name": "New Crew Operator", "email": "new@nyxara.example",
                                       "password": "Strong12345pw", "confirm": "Strong12345pw"}, follow_redirects=True)
    assert r.status_code == 200 and b"Operator role" in r.data
    with app.app_context():
        u = User.query.filter_by(email="new@nyxara.example").one()
        assert u.role == "operator"


def test_register_invalid_rejected(client, app):
    r = client.post("/register", data={"full_name": "X", "email": "not-an-email", "password": "short", "confirm": "other"})
    assert r.status_code == 200
    assert b"Invalid email address" in r.data and b"at least 10 characters" in r.data and b"Passwords must match" in r.data
    with app.app_context():
        assert User.query.count() == 3


def test_register_duplicate_email_rejected(client):
    r = client.post("/register", data={"full_name": "Dup User", "email": "admin@nyxara.example",
                                       "password": "Strong12345pw", "confirm": "Strong12345pw"})
    assert b"already exists" in r.data


def test_login_correct(client, app):
    r = login(client, "admin")
    assert r.status_code == 200 and b"Mission Dashboard" in r.data
    with app.app_context():
        assert AuditLog.query.filter_by(action="login").count() == 1


def test_login_incorrect(client):
    r = client.post("/login", data={"email": "admin@nyxara.example", "password": "wrong-password1"})
    assert b"Invalid email or password" in r.data
    assert client.get("/dashboard").status_code == 302


def test_login_inactive_account_blocked(client, app):
    with app.app_context():
        u = User.query.filter_by(email="operator@nyxara.example").one()
        u.is_active_account = False
        from app.extensions import db
        db.session.commit()
    r = login(client, "operator")
    assert b"Invalid email or password" in r.data


def test_logout(client):
    login(client, "doctor")
    r = client.post("/logout", follow_redirects=True)
    assert b"signed out" in r.data
    assert client.get("/dashboard").status_code == 302


def test_protected_routes_redirect_to_login(client):
    for url in ["/dashboard", "/astronauts", "/measurements", "/alerts", "/missions", "/users", "/reports", "/settings"]:
        r = client.get(url)
        assert r.status_code == 302 and "/login" in r.headers["Location"], url


def test_open_redirect_blocked(client):
    r = client.post("/login?next=https://evil.example/", data={"email": "admin@nyxara.example", "password": "AdminPass2026x"})
    assert r.headers["Location"].endswith("/dashboard")


def test_change_password(as_role, app):
    c = as_role("operator")
    r = c.post("/settings", data={"current": "OperPass2026x", "password": "NewOper2026xx", "confirm": "NewOper2026xx"}, follow_redirects=True)
    assert b"Password updated" in r.data
    with app.app_context():
        assert User.query.filter_by(email="operator@nyxara.example").one().check_password("NewOper2026xx")
