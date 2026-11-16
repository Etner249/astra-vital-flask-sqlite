"""JSON API v1 used by the GitHub Pages frontend: Bearer auth, CORS, permissions, CRUD, demo limits."""
from datetime import timedelta
import pytest
from app.demo import DEMO_ACCOUNTS, ensure_demo_accounts
from app.extensions import db
from app.models import ApiToken, Astronaut, HealthMeasurement, User, utcnow
from tests.conftest import PW

ORIGIN = "https://etner249.github.io"
API = "/api/v1"


def token_for(client, email, password):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password}, headers={"Origin": ORIGIN})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["token"]


@pytest.fixture
def tok(client):
    cache = {}

    def _t(role):
        if role not in cache:
            cache[role] = token_for(client, f"{role}@nyxara.example", PW[role])
        return {"Authorization": f"Bearer {cache[role]}", "Origin": ORIGIN}
    return _t


# ---------------------------------------------------------------- CORS / public
def test_health_and_cors_allowed_origin(client):
    r = client.get(f"{API}/health", headers={"Origin": ORIGIN})
    assert r.status_code == 200 and r.get_json()["status"] == "ok"
    assert r.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Access-Control-Allow-Credentials" not in r.headers  # bearer tokens, no cookies


def test_cors_rejects_other_origins(client):
    for evil in ("https://evil.example", "https://etner249.github.io.evil.example", "http://etner249.github.io"):
        r = client.get(f"{API}/health", headers={"Origin": evil})
        assert r.status_code == 403
        assert "Access-Control-Allow-Origin" not in r.headers


def test_preflight(client):
    r = client.options(f"{API}/astronauts", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                                                     "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 204
    assert r.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Authorization" in r.headers["Access-Control-Allow-Headers"]
    assert "DELETE" in r.headers["Access-Control-Allow-Methods"]


def test_demo_accounts_endpoint(app, client):
    accs = client.get(f"{API}/demo-accounts").get_json()["accounts"]
    assert [a["email"] for a in accs] == [a["email"] for a in DEMO_ACCOUNTS]
    app.config["DEMO_ACCOUNTS_ENABLED"] = False
    assert client.get(f"{API}/demo-accounts").get_json()["accounts"] == []


# ---------------------------------------------------------------- auth
def test_login_returns_hashed_token_and_me(app, client):
    r = client.post(f"{API}/auth/login", json={"email": "doctor@nyxara.example", "password": PW["doctor"]})
    body = r.get_json()
    assert r.status_code == 200 and body["token_type"] == "Bearer" and body["user"]["role"] == "doctor"
    assert "alerts.manage" in body["user"]["permissions"] and "users.manage" not in body["user"]["permissions"]
    assert "Set-Cookie" not in r.headers or "session=" not in r.headers.get("Set-Cookie", "")
    with app.app_context():
        stored = ApiToken.query.one()
        assert stored.token_hash != body["token"] and len(stored.token_hash) == 64
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200 and me.get_json()["user"]["email"] == "doctor@nyxara.example"


def test_login_wrong_password_and_unknown_user(client):
    for email, pw in (("doctor@nyxara.example", "wrong-pass-1"), ("ghost@nyxara.example", "whatever123")):
        r = client.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 401 and r.get_json()["error"] == "Invalid email or password."


def test_requests_without_or_with_bad_token_are_401(client):
    assert client.get(f"{API}/astronauts").status_code == 401
    assert client.get(f"{API}/astronauts", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_cookie_session_is_not_accepted_by_api(client):
    client.post("/login", data={"email": "admin@nyxara.example", "password": PW["admin"]})
    assert client.get("/dashboard").status_code == 200       # HTML session works
    assert client.get(f"{API}/astronauts").status_code == 401  # API ignores cookies (CSRF-safe)


def test_logout_revokes_token(client, tok):
    h = tok("operator")
    assert client.post(f"{API}/auth/logout", headers=h).status_code == 200
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401


def test_expired_and_inactive(app, client, tok):
    h = tok("operator")
    with app.app_context():
        t = ApiToken.query.one()
        t.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    h2 = {"Authorization": "Bearer " + token_for(client, "doctor@nyxara.example", PW["doctor"])}
    # the test app context is shared with the test client requests, so update through the same session
    User.query.filter_by(email="doctor@nyxara.example").one().is_active_account = False
    db.session.commit()
    assert client.get(f"{API}/auth/me", headers=h2).status_code == 401


def test_login_rate_limited(app, client):
    app.config["API_LOGIN_MAX_FAILS"] = 3
    for _ in range(3):
        client.post(f"{API}/auth/login", json={"email": "x@nyxara.example", "password": "bad-password1"})
    r = client.post(f"{API}/auth/login", json={"email": "admin@nyxara.example", "password": PW["admin"]})
    assert r.status_code == 429


# ---------------------------------------------------------------- permissions
@pytest.mark.parametrize("role,method,path,body,expected", [
    ("operator", "post", "/astronauts", {"code": "AV-X-01", "full_name": "X Person", "status": "active"}, 403),
    ("doctor", "post", "/astronauts", {"code": "AV-X-01", "full_name": "X Person", "status": "active"}, 403),
    ("admin", "post", "/astronauts", {"code": "AV-X-01", "full_name": "X Person", "status": "active"}, 201),
    ("operator", "get", "/users", None, 403),
    ("doctor", "get", "/users", None, 403),
    ("admin", "get", "/users", None, 200),
    ("operator", "get", "/audit", None, 403),
    ("doctor", "get", "/audit", None, 403),
    ("admin", "get", "/audit", None, 200),
    ("operator", "get", "/reports/summary", None, 403),
    ("doctor", "get", "/reports/summary", None, 200),
    ("operator", "post", "/missions", {"code": "AV-M-9", "name": "M", "environment": "moon", "start_date": "2026-01-01", "duration_days": 10, "status": "planned"}, 403),
    ("operator", "get", "/astronauts", None, 200),
    ("operator", "get", "/alerts", None, 200),
])
def test_permission_matrix(client, tok, role, method, path, body, expected):
    r = getattr(client, method)(API + path, json=body, headers=tok(role))
    assert r.status_code == expected, r.get_json()


def test_operator_can_create_but_not_edit_or_delete_measurements(app, client, tok):
    r = client.post(f"{API}/measurements", json={"astronaut_id": 1, "heart_rate": 72}, headers=tok("operator"))
    assert r.status_code == 201
    mid = r.get_json()["item"]["id"]
    assert client.put(f"{API}/measurements/{mid}", json={"heart_rate": 80}, headers=tok("operator")).status_code == 403
    assert client.delete(f"{API}/measurements/{mid}", headers=tok("operator")).status_code == 403
    assert client.put(f"{API}/measurements/{mid}", json={"heart_rate": 80}, headers=tok("doctor")).status_code == 200
    assert client.delete(f"{API}/measurements/{mid}", headers=tok("doctor")).status_code == 403
    assert client.delete(f"{API}/measurements/{mid}", headers=tok("admin")).status_code == 200


# ---------------------------------------------------------------- CRUD + engine
def test_measurement_with_original_indicators_generates_alerts(app, client, tok):
    r = client.post(f"{API}/measurements", headers=tok("doctor"), json={
        "astronaut_id": 1, "measured_at": (utcnow() - timedelta(hours=1)).isoformat() + "Z",
        "glucose": 50, "fatigue": 6, "sleep_hours": 6.5, "mood": 4, "exercise_min": 90, "notes": "api test"})
    body = r.get_json()
    assert r.status_code == 201, body
    levels = {a["metric"]: a["level"] for a in body["alerts"]}
    assert levels["glucose"] == "priority" and levels["fatigue"] == "followup" and levels["sleep_hours"] == "info"
    assert body["item"]["glucose"] == 50 and body["item"]["sleep_hours"] == 6.5
    with app.app_context():
        assert HealthMeasurement.query.count() == 1  # persisted in SQLite


def test_measurement_validation_and_filters(client, tok):
    h = tok("admin")
    assert client.post(f"{API}/measurements", json={"astronaut_id": 1}, headers=h).status_code == 422
    r = client.post(f"{API}/measurements", json={"astronaut_id": 1, "fatigue": 9}, headers=h)
    assert r.status_code == 422 and "fatigue" in r.get_json()["fields"]
    future = (utcnow() + timedelta(days=1)).isoformat()
    assert client.post(f"{API}/measurements", json={"astronaut_id": 1, "heart_rate": 70, "measured_at": future}, headers=h).status_code == 422
    for day in ("2026-11-01T08:00:00Z", "2026-11-05T08:00:00Z"):
        assert client.post(f"{API}/measurements", json={"astronaut_id": 1, "heart_rate": 70, "measured_at": day}, headers=h).status_code == 201
    r = client.get(f"{API}/measurements?astronaut_id=1&from=2026-11-04&to=2026-11-05", headers=h).get_json()
    assert r["total"] == 1 and r["items"][0]["measured_at"].startswith("2026-11-05")


def test_astronaut_and_mission_crud(app, client, tok):
    h = tok("admin")
    r = client.post(f"{API}/missions", headers=h, json={"code": "AV-API-1", "name": "API mission", "environment": "mars",
                                                        "start_date": "2026-11-01", "duration_days": 300, "status": "active"})
    assert r.status_code == 201
    mid = r.get_json()["item"]["id"]
    r = client.post(f"{API}/astronauts", headers=h, json={"code": "AV-API-01", "full_name": "Api Crew", "status": "active", "mission_id": mid})
    assert r.status_code == 201 and r.get_json()["item"]["mission"]["code"] == "AV-API-1"
    aid = r.get_json()["item"]["id"]
    assert client.post(f"{API}/astronauts", headers=h, json={"code": "AV-API-01", "full_name": "Dup", "status": "active"}).status_code == 422
    r = client.put(f"{API}/astronauts/{aid}", headers=h, json={"code": "AV-API-01", "full_name": "Api Crew Edited", "status": "returned", "mission_id": mid})
    assert r.status_code == 200 and r.get_json()["item"]["status"] == "returned"
    assert client.get(f"{API}/astronauts/{aid}", headers=h).get_json()["item"]["full_name"] == "Api Crew Edited"
    assert client.delete(f"{API}/missions/{mid}", headers=h).status_code == 409  # still has astronauts
    assert client.delete(f"{API}/astronauts/{aid}", headers=h).status_code == 200
    assert client.delete(f"{API}/missions/{mid}", headers=h).status_code == 200
    assert client.get(f"{API}/astronauts/{aid}", headers=h).status_code == 404
    assert client.get(f"{API}/astronauts/{aid}", headers=h).is_json


def test_alert_review(client, tok):
    r = client.post(f"{API}/measurements", json={"astronaut_id": 1, "spo2": 88}, headers=tok("operator"))
    al = r.get_json()["alerts"][0]
    assert al["level"] == "priority"
    assert client.patch(f"{API}/alerts/{al['id']}", json={"status": "resolved"}, headers=tok("operator")).status_code == 403
    r = client.patch(f"{API}/alerts/{al['id']}", json={"status": "acknowledged", "review_notes": "Re-measured: 96%"}, headers=tok("doctor"))
    assert r.status_code == 200 and r.get_json()["item"]["reviewed_by"] == "Test doctor"
    assert client.get(f"{API}/alerts?status=acknowledged", headers=tok("operator")).get_json()["items"][0]["id"] == al["id"]


def test_user_management_by_private_admin(client, tok):
    h = tok("admin")
    r = client.post(f"{API}/users", headers=h, json={"full_name": "New Doc", "email": "newdoc@nyxara.example", "role": "doctor",
                                                     "password": "Abcdefgh12345", "is_active_account": True})
    assert r.status_code == 201
    uid = r.get_json()["item"]["id"]
    assert client.delete(f"{API}/users/{uid}", headers=h).status_code == 200


# ---------------------------------------------------------------- demo accounts
def test_demo_accounts_via_api(app, client):
    with app.app_context():
        ensure_demo_accounts()
        a = Astronaut(code="AV-SYN-9", full_name="Synthetic Nine", is_synthetic=True)
        db.session.add(a)
        db.session.commit()
        syn_id = a.id
    accs = {x["role"]: x for x in DEMO_ACCOUNTS}
    roles = {}
    for role, acc in accs.items():
        r = client.post(f"{API}/auth/login", json={"email": acc["email"], "password": acc["password"]})
        assert r.status_code == 200 and r.get_json()["user"]["role"] == role and r.get_json()["user"]["is_demo"]
        roles[role] = {"Authorization": "Bearer " + r.get_json()["token"]}
    adm = roles["admin"]
    r = client.get(f"{API}/users", headers=adm).get_json()
    assert r["read_only"] is True and all("admin@nyxara.example" != u["email"] for u in r["items"])
    assert client.post(f"{API}/users", headers=adm, json={"full_name": "X", "email": "x@nyxara.example", "role": "admin",
                                                          "password": "Abcdefgh12345", "is_active_account": True}).status_code == 403
    assert client.delete(f"{API}/astronauts/{syn_id}", headers=adm).status_code == 403
    audit = client.get(f"{API}/audit", headers=adm).get_json()["items"]
    assert all(x["ip_address"] in (None, "hidden") for x in audit)
    assert client.get(f"{API}/audit", headers=roles["doctor"]).status_code == 403
    assert client.get(f"{API}/reports/summary", headers=roles["operator"]).status_code == 403


def test_api_post_is_csrf_exempt_but_needs_bearer(app, client, tok):
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post(f"{API}/measurements", json={"astronaut_id": 1, "heart_rate": 70}).status_code == 401
    assert client.post(f"{API}/measurements", json={"astronaut_id": 1, "heart_rate": 70}, headers=tok("operator")).status_code == 201
    # HTML forms still require CSRF
    client.post("/login", data={"email": "admin@nyxara.example", "password": PW["admin"]})
