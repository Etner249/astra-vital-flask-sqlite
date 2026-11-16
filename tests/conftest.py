import pytest
from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import User, Mission, Astronaut
from datetime import date

PW = {"admin": "AdminPass2026x", "doctor": "DoctorPass2026x", "operator": "OperPass2026x"}


@pytest.fixture
def app(tmp_path):
    # Real SQLite database file per test (not an in-memory substitute)
    app = create_app(TestConfig, SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}")
    with app.app_context():
        db.create_all()
        for role in PW:
            u = User(full_name=f"Test {role}", email=f"{role}@nyxara.example", role=role)
            u.set_password(PW[role])
            db.session.add(u)
        m = Mission(code="AV-TEST-1", name="Test mission", environment="station", start_date=date(2026, 1, 1), duration_days=90, status="active")
        db.session.add(m)
        db.session.flush()
        db.session.add(Astronaut(code="AV-T-01", full_name="Test Astronaut One", demo_age=40, mission_id=m.id))
        db.session.commit()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, role):
    return client.post("/login", data={"email": f"{role}@nyxara.example", "password": PW[role]}, follow_redirects=True)


@pytest.fixture
def as_role(client):
    def _as(role):
        login(client, role)
        return client
    return _as
