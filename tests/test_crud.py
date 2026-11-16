from app.extensions import db
from app.models import Astronaut, HealthMeasurement, HealthAlert, Mission, User, AuditLog


def test_create_astronaut(as_role, app):
    c = as_role("admin")
    r = c.post("/astronauts/new", data={"code": "AV-T-02", "full_name": "Test Astronaut Two", "demo_age": 35, "mission_id": 1, "status": "active"}, follow_redirects=True)
    assert b"registered" in r.data
    with app.app_context():
        a = Astronaut.query.filter_by(code="AV-T-02").one()
        assert a.mission.code == "AV-TEST-1"
        assert AuditLog.query.filter_by(action="create", entity="astronaut").count() == 1


def test_create_astronaut_duplicate_code(as_role):
    r = as_role("admin").post("/astronauts/new", data={"code": "AV-T-01", "full_name": "Duplicate", "mission_id": 0, "status": "active"})
    assert b"already exists" in r.data


def test_read_astronaut(as_role):
    c = as_role("operator")
    assert b"AV-T-01" in c.get("/astronauts").data
    assert b"Test Astronaut One" in c.get("/astronauts/1").data
    assert b"AV-T-01" in c.get("/astronauts?q=T-01").data


def test_update_astronaut(as_role, app):
    r = as_role("admin").post("/astronauts/1/edit", data={"code": "AV-T-01", "full_name": "Renamed Astronaut", "demo_age": 41, "mission_id": 0, "status": "returned"}, follow_redirects=True)
    assert b"updated" in r.data
    with app.app_context():
        a = db.session.get(Astronaut, 1)
        assert a.full_name == "Renamed Astronaut" and a.status == "returned" and a.mission_id is None


def test_delete_astronaut_cascades(as_role, app):
    c = as_role("admin")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "spo2": 88})
    with app.app_context():
        assert HealthMeasurement.query.count() == 1 and HealthAlert.query.count() == 1
    r = c.post("/astronauts/1/delete", data={"confirm_open_alerts": "yes"}, follow_redirects=True)
    assert b"deleted" in r.data
    with app.app_context():
        assert db.session.get(Astronaut, 1) is None
        assert HealthMeasurement.query.count() == 0 and HealthAlert.query.count() == 0


def test_delete_astronaut_with_open_priority_needs_confirmation(as_role, app):
    c = as_role("admin")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "temperature": 38.6})
    r = c.post("/astronauts/1/delete", follow_redirects=True)
    assert b"open priority alerts" in r.data
    with app.app_context():
        assert db.session.get(Astronaut, 1) is not None


def test_create_measurement(as_role, app):
    r = as_role("operator").post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 72,
                                                              "systolic_bp": 118, "diastolic_bp": 76, "spo2": 98, "temperature": 36.7, "respiratory_rate": 14,
                                                              "notes": "post-exercise"}, follow_redirects=True)
    assert b"Measurement saved" in r.data
    with app.app_context():
        m = HealthMeasurement.query.one()
        assert m.heart_rate == 72 and not m.is_synthetic and m.recorded_by.email == "operator@nyxara.example"
        assert HealthAlert.query.count() == 0  # all values within references


def test_read_and_filter_measurements(as_role):
    c = as_role("doctor")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-01T08:00", "heart_rate": 70})
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 71})
    r = c.get("/measurements?astronaut_id=1&from=2026-11-05&to=2026-11-30")
    assert r.status_code == 200 and b"2026-11-10 08:00" in r.data and b"2026-11-01 08:00" not in r.data


def test_update_measurement_regenerates_alerts(as_role, app):
    c = as_role("doctor")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "spo2": 98})
    with app.app_context():
        assert HealthAlert.query.count() == 0
    c.post("/measurements/1/edit", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "spo2": 89})
    with app.app_context():
        assert db.session.get(HealthMeasurement, 1).spo2 == 89
        assert HealthAlert.query.filter_by(level="priority", metric="spo2").count() == 1


def test_delete_measurement(as_role, app):
    c = as_role("admin")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 70})
    r = c.post("/measurements/1/delete", data={"next": "/measurements"}, follow_redirects=True)
    assert b"Measurement deleted" in r.data
    with app.app_context():
        assert HealthMeasurement.query.count() == 0


def test_generate_alert_persisted_with_explanation(as_role, app):
    as_role("operator").post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "temperature": 38.4, "heart_rate": 108})
    with app.app_context():
        alerts = {a.metric: a for a in HealthAlert.query.all()}
        assert alerts["temperature"].level == "priority" and "CDC" in alerts["temperature"].source_ref
        assert alerts["heart_rate"].level == "followup"
        for a in alerts.values():
            assert a.what_changed and a.why and a.action and a.contact and a.status == "open" and a.astronaut_id == 1


def test_baseline_rule_generates_followup(as_role, app):
    c = as_role("doctor")
    for d, hr in enumerate([66, 67, 65, 66, 67, 66, 65], start=1):
        c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": f"2026-11-{d:02d}T08:00", "heart_rate": hr})
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-09T08:00", "heart_rate": 85})
    with app.app_context():
        a = HealthAlert.query.filter_by(metric="heart_rate").one()
        assert a.rule == "baseline" and "baseline" in a.why


def test_update_alert_status(as_role, app):
    c = as_role("doctor")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "spo2": 88})
    r = c.post("/alerts/1", data={"status": "acknowledged", "review_notes": "Re-measured, contacting flight surgeon."}, follow_redirects=True)
    assert b"Alert updated" in r.data
    with app.app_context():
        a = db.session.get(HealthAlert, 1)
        assert a.status == "acknowledged" and a.reviewed_by.email == "doctor@nyxara.example" and a.reviewed_at


def test_mission_crud_and_restricted_delete(as_role, app):
    c = as_role("admin")
    c.post("/missions/new", data={"code": "AV-NEW-9", "name": "New mission", "environment": "moon", "start_date": "2027-01-01", "duration_days": 30, "status": "planned"})
    with app.app_context():
        m = Mission.query.filter_by(code="AV-NEW-9").one()
        mid = m.id
    c.post(f"/missions/{mid}/edit", data={"code": "AV-NEW-9", "name": "Edited mission", "environment": "mars", "start_date": "2027-02-01", "duration_days": 60, "status": "planned"})
    with app.app_context():
        assert db.session.get(Mission, mid).name == "Edited mission"
    r = c.post("/missions/1/delete", follow_redirects=True)  # has an astronaut assigned
    assert b"Reassign them" in r.data
    c.post(f"/missions/{mid}/delete")
    with app.app_context():
        assert db.session.get(Mission, mid) is None and db.session.get(Mission, 1) is not None


def test_user_management_by_admin(as_role, app):
    c = as_role("admin")
    c.post("/users/new", data={"full_name": "New Doctor", "email": "nd@nyxara.example", "role": "doctor", "password": "Doctor12345x", "is_active_account": "y"})
    with app.app_context():
        u = User.query.filter_by(email="nd@nyxara.example").one()
        uid = u.id
        assert u.role == "doctor" and u.check_password("Doctor12345x")
    c.post(f"/users/{uid}/edit", data={"full_name": "New Doctor", "email": "nd@nyxara.example", "role": "operator", "is_active_account": "y"})
    with app.app_context():
        assert db.session.get(User, uid).role == "operator"
    c.post(f"/users/{uid}/delete")
    with app.app_context():
        assert db.session.get(User, uid) is None


def test_admin_cannot_delete_self(as_role, app):
    r = as_role("admin").post("/users/1/delete", follow_redirects=True)
    assert b"cannot delete your own account" in r.data


def test_reports_csv(as_role):
    c = as_role("doctor")
    c.post("/measurements/new", data={"astronaut_id": 1, "measured_at": "2026-11-10T08:00", "heart_rate": 70})
    r = c.get("/reports/measurements.csv")
    assert r.status_code == 200 and r.mimetype == "text/csv" and b"AV-T-01" in r.data
