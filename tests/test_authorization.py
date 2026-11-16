import pytest

ALL = ["/dashboard", "/astronauts", "/astronauts/1", "/measurements", "/alerts", "/missions", "/risks", "/nasa-data", "/settings"]


@pytest.mark.parametrize("url", ALL + ["/users", "/users/new", "/reports", "/audit", "/astronauts/new", "/astronauts/1/edit", "/missions/new"])
def test_admin_authorized_everywhere(as_role, url):
    assert as_role("admin").get(url).status_code == 200


@pytest.mark.parametrize("url", ALL + ["/reports", "/measurements/new"])
def test_doctor_authorized(as_role, url):
    assert as_role("doctor").get(url).status_code == 200


@pytest.mark.parametrize("url", ALL + ["/measurements/new"])
def test_operator_authorized(as_role, url):
    assert as_role("operator").get(url).status_code == 200


@pytest.mark.parametrize("role,url", [
    ("operator", "/users"), ("operator", "/reports"), ("operator", "/astronauts/new"), ("operator", "/astronauts/1/edit"),
    ("operator", "/missions/new"), ("operator", "/audit"),
    ("doctor", "/users"), ("doctor", "/users/new"), ("doctor", "/astronauts/new"), ("doctor", "/missions/new"), ("doctor", "/audit"),
])
def test_access_denied_by_role(as_role, role, url):
    assert as_role(role).get(url).status_code == 403


def test_operator_cannot_post_to_admin_endpoints(as_role, app):
    c = as_role("operator")
    assert c.post("/astronauts/1/delete").status_code == 403
    assert c.post("/users/new", data={"full_name": "Hacker Admin", "email": "h@nyxara.example", "role": "admin", "password": "Hacker12345x"}).status_code == 403
    from app.models import User
    with app.app_context():
        assert User.query.filter_by(email="h@nyxara.example").count() == 0


def test_operator_cannot_edit_or_delete_measurement(as_role, app):
    c = as_role("operator")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 70})
    assert c.get("/measurements/1/edit").status_code == 403
    assert c.post("/measurements/1/delete").status_code == 403


def test_operator_cannot_manage_alerts(as_role):
    c = as_role("operator")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "spo2": 88})
    assert c.post("/alerts/1", data={"status": "resolved"}).status_code == 403
