"""SQLAlchemy models — ASTRA VITAL Academic Edition (SQLite)."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import CheckConstraint, Index
from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


ROLES = ("admin", "doctor", "operator")
ROLE_LABELS = {"admin": "Administrator", "doctor": "Doctor / Specialist", "operator": "Operator"}


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="operator")
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime)
    is_demo = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text("0"))  # public demo account
    __table_args__ = (CheckConstraint("role IN ('admin','doctor','operator')", name="role_valid"),)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)


class Mission(TimestampMixin, db.Model):
    __tablename__ = "missions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    environment = db.Column(db.String(40), nullable=False, default="station")
    start_date = db.Column(db.Date, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False, default=180)
    status = db.Column(db.String(20), nullable=False, default="planned")
    description = db.Column(db.Text)
    is_synthetic = db.Column(db.Boolean, nullable=False, default=False)
    # ondelete RESTRICT: a mission with assigned astronauts cannot be deleted (controlled deletion)
    astronauts = db.relationship("Astronaut", back_populates="mission", passive_deletes="all")
    __table_args__ = (
        CheckConstraint("duration_days BETWEEN 1 AND 1500", name="duration_range"),
        CheckConstraint("status IN ('planned','active','completed')", name="status_valid"),
    )


class Astronaut(TimestampMixin, db.Model):
    __tablename__ = "astronauts"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    demo_age = db.Column(db.Integer)
    role_on_board = db.Column(db.String(60))
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id", ondelete="RESTRICT"), index=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    notes = db.Column(db.Text)
    is_synthetic = db.Column(db.Boolean, nullable=False, default=False)
    mission = db.relationship("Mission", back_populates="astronauts")
    measurements = db.relationship("HealthMeasurement", back_populates="astronaut", cascade="all, delete-orphan",
                                   order_by="HealthMeasurement.measured_at.desc()")
    alerts = db.relationship("HealthAlert", back_populates="astronaut", cascade="all, delete-orphan",
                             order_by="HealthAlert.created_at.desc()")
    __table_args__ = (
        CheckConstraint("demo_age IS NULL OR demo_age BETWEEN 18 AND 80", name="age_range"),
        CheckConstraint("status IN ('active','inactive','returned')", name="status_valid"),
    )


class HealthMeasurement(TimestampMixin, db.Model):
    __tablename__ = "health_measurements"
    id = db.Column(db.Integer, primary_key=True)
    astronaut_id = db.Column(db.Integer, db.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False)
    measured_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    heart_rate = db.Column(db.Integer)              # bpm
    systolic_bp = db.Column(db.Integer)             # mmHg
    diastolic_bp = db.Column(db.Integer)            # mmHg
    spo2 = db.Column(db.Float)                      # %
    temperature = db.Column(db.Float)               # °C
    respiratory_rate = db.Column(db.Integer)        # breaths/min
    # indicators of the original ASTRA VITAL (NASA Space Apps 2026) app
    sleep_hours = db.Column(db.Float)               # h, last sleep period
    exercise_min = db.Column(db.Integer)            # min of prescribed exercise
    fatigue = db.Column(db.Integer)                 # Samn-Perelli 1–7
    mood = db.Column(db.Integer)                    # 1–5 self-report
    glucose = db.Column(db.Integer)                 # mg/dL
    notes = db.Column(db.Text)
    source = db.Column(db.String(40), nullable=False, default="manual")  # manual | synthetic_demo
    is_synthetic = db.Column(db.Boolean, nullable=False, default=False)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    astronaut = db.relationship("Astronaut", back_populates="measurements")
    recorded_by = db.relationship("User")
    alerts = db.relationship("HealthAlert", back_populates="measurement", passive_deletes=True)
    __table_args__ = (
        Index("ix_measurements_astronaut_time", "astronaut_id", "measured_at"),
        CheckConstraint("heart_rate IS NULL OR heart_rate BETWEEN 25 AND 230", name="hr_range"),
        CheckConstraint("systolic_bp IS NULL OR systolic_bp BETWEEN 60 AND 260", name="sbp_range"),
        CheckConstraint("diastolic_bp IS NULL OR diastolic_bp BETWEEN 30 AND 160", name="dbp_range"),
        CheckConstraint("spo2 IS NULL OR spo2 BETWEEN 50 AND 100", name="spo2_range"),
        CheckConstraint("temperature IS NULL OR temperature BETWEEN 32 AND 43", name="temp_range"),
        CheckConstraint("respiratory_rate IS NULL OR respiratory_rate BETWEEN 4 AND 60", name="rr_range"),
        CheckConstraint("sleep_hours IS NULL OR sleep_hours BETWEEN 0 AND 16", name="sleep_range"),
        CheckConstraint("exercise_min IS NULL OR exercise_min BETWEEN 0 AND 400", name="exercise_range"),
        CheckConstraint("fatigue IS NULL OR fatigue BETWEEN 1 AND 7", name="fatigue_range"),
        CheckConstraint("mood IS NULL OR mood BETWEEN 1 AND 5", name="mood_range"),
        CheckConstraint("glucose IS NULL OR glucose BETWEEN 20 AND 600", name="glucose_range"),
    )

    VITAL_FIELDS = ("heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature", "respiratory_rate",
                    "sleep_hours", "exercise_min", "fatigue", "mood", "glucose")


class HealthAlert(TimestampMixin, db.Model):
    __tablename__ = "health_alerts"
    id = db.Column(db.Integer, primary_key=True)
    astronaut_id = db.Column(db.Integer, db.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False)
    measurement_id = db.Column(db.Integer, db.ForeignKey("health_measurements.id", ondelete="SET NULL"), index=True)
    level = db.Column(db.String(10), nullable=False)          # info | followup | priority
    metric = db.Column(db.String(30), nullable=False)
    rule = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    what_changed = db.Column(db.Text, nullable=False)
    why = db.Column(db.Text, nullable=False)
    action = db.Column(db.Text, nullable=False)
    contact = db.Column(db.Text, nullable=False)
    source_ref = db.Column(db.Text)
    status = db.Column(db.String(15), nullable=False, default="open")  # open | acknowledged | resolved
    review_notes = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = db.Column(db.DateTime)
    astronaut = db.relationship("Astronaut", back_populates="alerts")
    measurement = db.relationship("HealthMeasurement", back_populates="alerts")
    reviewed_by = db.relationship("User")
    __table_args__ = (
        Index("ix_alerts_status_level", "status", "level"),
        CheckConstraint("level IN ('info','followup','priority')", name="level_valid"),
        CheckConstraint("status IN ('open','acknowledged','resolved')", name="status_valid"),
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(20), nullable=False)   # create | update | delete | login | logout | ...
    entity = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user = db.relationship("User")


class ApiToken(db.Model):
    """Bearer tokens for the JSON API used by the GitHub Pages frontend.
    Only a SHA-256 hash of the token is stored; tokens expire and are revoked on logout."""
    __tablename__ = "api_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    user = db.relationship("User")
