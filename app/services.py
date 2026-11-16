from flask import request
from flask_login import current_user
from .extensions import db
from .models import AuditLog, HealthAlert, HealthMeasurement
from .engine import analyze_measurement


def log_action(action, entity, entity_id=None, details=None, user=None):
    u = user or (current_user if getattr(current_user, "is_authenticated", False) else None)
    db.session.add(AuditLog(user_id=u.id if u else None, action=action, entity=entity, entity_id=entity_id,
                            details=(details or "")[:500], ip_address=(request.remote_addr if request else None)))


def generate_alerts(measurement):
    """(Re)generate engine alerts for one measurement and persist them in SQLite.
    Open alerts of this measurement are replaced; alerts already reviewed are kept (audit trail)."""
    db.session.flush()
    HealthAlert.query.filter_by(measurement_id=measurement.id, status="open").delete()
    reviewed_metrics = {a.metric for a in HealthAlert.query.filter(HealthAlert.measurement_id == measurement.id,
                                                                    HealthAlert.status != "open")}
    history = (HealthMeasurement.query
               .filter(HealthMeasurement.astronaut_id == measurement.astronaut_id,
                       HealthMeasurement.measured_at < measurement.measured_at,
                       HealthMeasurement.id != measurement.id)
               .order_by(HealthMeasurement.measured_at.asc()).all())
    created = []
    for d in analyze_measurement(measurement, history):
        if d.metric in reviewed_metrics:
            continue
        a = HealthAlert(astronaut_id=measurement.astronaut_id, measurement_id=measurement.id, level=d.level,
                        metric=d.metric, rule=d.rule, title=d.title, what_changed=d.what_changed, why=d.why,
                        action=d.action, contact=d.contact, source_ref=d.source_ref)
        db.session.add(a)
        created.append(a)
    return created
