from functools import wraps
from flask import abort
from flask_login import current_user, login_required

# Backend permission matrix (enforced on every route, not only by hiding buttons)
PERMISSIONS = {
    "dashboard.view": {"admin", "doctor", "operator"},
    "astronauts.view": {"admin", "doctor", "operator"},
    "astronauts.manage": {"admin"},
    "missions.view": {"admin", "doctor", "operator"},
    "missions.manage": {"admin"},
    "measurements.view": {"admin", "doctor", "operator"},
    "measurements.create": {"admin", "doctor", "operator"},
    "measurements.edit": {"admin", "doctor"},
    "measurements.delete": {"admin"},
    "alerts.view": {"admin", "doctor", "operator"},
    "alerts.manage": {"admin", "doctor"},
    "alerts.delete": {"admin"},
    "users.manage": {"admin"},
    "reports.view": {"admin", "doctor"},
    "audit.view": {"admin"},
}


def can(permission, user=None):
    u = user or current_user
    return bool(getattr(u, "is_authenticated", False)) and u.role in PERMISSIONS.get(permission, set())


def permission_required(permission):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if not can(permission):
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco
