"""JSON API (v1) for the ASTRA VITAL frontend published on GitHub Pages (https://etner249.github.io/astra-vital/).

Authentication: Bearer tokens only (no cookies), so the cross-site frontend works in every browser and
CSRF does not apply. Tokens are random 256-bit values; only their SHA-256 hash is stored (api_tokens table),
they expire after API_TOKEN_HOURS and are revoked on logout.
CORS: only the origins listed in CORS_ORIGINS (default https://etner249.github.io) receive CORS headers.
Authorization: the same backend permission matrix (app/decorators.py) and public-demo limits (app/demo.py)
used by the server-rendered pages.
"""
import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request, abort, Response
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import HTTPException

from .decorators import PERMISSIONS, can
from .demo import DEMO_ACCOUNTS, demo_forbidden, is_demo_user, mask_email
from .engine import METRICS as ENGINE_METRICS, overall_status
from .extensions import csrf, db
from .forms import AstronautForm, MeasurementForm, MissionForm, UserForm, AlertReviewForm
from .models import (ApiToken, Astronaut, AuditLog, HealthAlert, HealthMeasurement, Mission, User, utcnow,
                     ROLE_LABELS)
from .services import generate_alerts, log_action

bp = Blueprint("api", __name__, url_prefix="/api/v1")
csrf.exempt(bp)

PUBLIC_ENDPOINTS = {"api.health", "api.demo_accounts", "api.login"}
BASELINE_MSG = "Public demo accounts cannot delete the synthetic reference data. Create a new record and delete it to test the operation."
_attempts = defaultdict(deque)  # ip -> timestamps of failed logins (per process)


# ------------------------------------------------------------------ helpers
def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if dt else None


def _err(status, message, **extra):
    resp = jsonify(dict(error=message, status=status, **extra))
    resp.status_code = status
    return resp


def _form(form_cls, data, obj=None):
    """Validate JSON with the same WTForms classes used by the HTML pages (single source of validation rules)."""
    md = MultiDict()
    for k, v in (data or {}).items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            if v:
                md.add(k, "y")
            continue
        md.add(k, str(v))
    form = form_cls(formdata=md, obj=obj, meta={"csrf": False})
    return form


def _form_errors(form):
    return {k: v for k, v in form.errors.items() if v}


def _require(permission):
    if not can(permission):
        abort(403, description="Your role does not have permission for this operation.")


def _parse_dt(value):
    """Accept ISO-8601 (with or without Z/offset) and return naive UTC."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ------------------------------------------------------------------ CORS + auth
def _allowed_origins():
    raw = current_app.config.get("CORS_ORIGINS", "https://etner249.github.io")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


@bp.before_request
def _authenticate():
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") not in _allowed_origins():
        return _err(403, "Origin not allowed.")
    if request.method == "OPTIONS":
        return Response(status=204)
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return _err(401, "Authentication required.")
    tok = ApiToken.query.filter_by(token_hash=_hash(header[7:].strip())).first()
    now = utcnow()
    if not tok or tok.revoked_at or tok.expires_at <= now or not tok.user or not tok.user.is_active_account:
        return _err(401, "Session expired or invalid. Please sign in again.")
    tok.last_used_at = now
    g._login_user = tok.user  # Flask-Login current_user for this request (cookie session is ignored)
    g.api_token = tok
    return None


@bp.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") in _allowed_origins():
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "600"
        resp.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    resp.headers.add("Vary", "Origin")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.errorhandler(HTTPException)
def _http_error(e):
    msg = e.description if e.description and not e.description.startswith(("You don't have", "The server")) else e.name
    return _err(e.code, msg)


# ------------------------------------------------------------------ serializers
def user_json(u, full=True):
    d = dict(id=u.id, full_name=u.full_name, email=mask_email(u.email), role=u.role, role_label=ROLE_LABELS.get(u.role, u.role),
             is_demo=bool(u.is_demo), is_active=bool(u.is_active_account))
    if full:
        d["last_login_at"] = _iso(u.last_login_at)
    return d


def mission_json(m):
    return dict(id=m.id, code=m.code, name=m.name, environment=m.environment, start_date=m.start_date.isoformat(),
                duration_days=m.duration_days, status=m.status, description=m.description or "",
                is_synthetic=bool(m.is_synthetic), astronauts=len(m.astronauts))


def astronaut_json(a):
    levels = [al.level for al in a.alerts if al.status == "open" and al.level != "info"]
    return dict(id=a.id, code=a.code, full_name=a.full_name, demo_age=a.demo_age, role_on_board=a.role_on_board or "",
                status=a.status, notes=a.notes or "", is_synthetic=bool(a.is_synthetic),
                mission=mission_json(a.mission) if a.mission else None, mission_id=a.mission_id,
                overall_status=overall_status(levels), open_alerts=len(levels), measurements=len(a.measurements))


def measurement_json(m):
    d = dict(id=m.id, astronaut_id=m.astronaut_id, astronaut_code=m.astronaut.code if m.astronaut else None,
             measured_at=_iso(m.measured_at), notes=m.notes or "", source=m.source, is_synthetic=bool(m.is_synthetic),
             recorded_by=m.recorded_by.full_name if m.recorded_by else None, created_at=_iso(m.created_at),
             updated_at=_iso(m.updated_at), alerts=len(m.alerts))
    for f in HealthMeasurement.VITAL_FIELDS:
        d[f] = getattr(m, f)
    return d


def alert_json(a):
    return dict(id=a.id, astronaut_id=a.astronaut_id, astronaut_code=a.astronaut.code if a.astronaut else None,
                measurement_id=a.measurement_id, level=a.level, metric=a.metric,
                metric_label=ENGINE_METRICS.get(a.metric, {}).get("label", a.metric), rule=a.rule, title=a.title,
                what_changed=a.what_changed, why=a.why, action=a.action, contact=a.contact, source_ref=a.source_ref,
                status=a.status, review_notes=a.review_notes or "",
                reviewed_by=a.reviewed_by.full_name if a.reviewed_by else None, reviewed_at=_iso(a.reviewed_at),
                created_at=_iso(a.created_at))


# ------------------------------------------------------------------ public
@bp.get("/health")
def health():
    return jsonify(status="ok", service="ASTRA VITAL Academic API", version="1",
                   time=_iso(utcnow()), demo_accounts=bool(current_app.config.get("DEMO_ACCOUNTS_ENABLED")))


@bp.get("/demo-accounts")
def demo_accounts():
    if not current_app.config.get("DEMO_ACCOUNTS_ENABLED"):
        return jsonify(accounts=[])
    keys = ("role", "label", "label_en", "email", "password", "can")
    return jsonify(accounts=[{k: a[k] for k in keys} for a in DEMO_ACCOUNTS],
                   warning="Public demo accounts: do not enter personal, medical or real data.")


@bp.post("/auth/login")
def login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    q = _attempts[ip]
    now = time.time()
    while q and now - q[0] > 300:
        q.popleft()
    if len(q) >= current_app.config.get("API_LOGIN_MAX_FAILS", 10):
        return _err(429, "Too many failed attempts. Wait a few minutes and try again.")
    data = request.get_json(silent=True) or {}
    email, pwd = str(data.get("email", "")).strip().lower()[:160], str(data.get("password", ""))[:128]
    user = User.query.filter_by(email=email).first() if email else None
    if not (user and user.is_active_account and user.check_password(pwd)):
        q.append(now)
        log_action("login_failed", "user", details=f"api: {email}")
        db.session.commit()
        return _err(401, "Invalid email or password.")
    token = secrets.token_urlsafe(32)
    hours = current_app.config.get("API_TOKEN_HOURS", 8)
    tok = ApiToken(user_id=user.id, token_hash=_hash(token), expires_at=utcnow() + timedelta(hours=hours))
    user.last_login_at = utcnow()
    db.session.add(tok)
    log_action("login", "user", user.id, "api (GitHub Pages frontend)", user=user)
    db.session.commit()
    g._login_user = user
    return jsonify(token=token, token_type="Bearer", expires_at=_iso(tok.expires_at), user=_me(user))


# ------------------------------------------------------------------ session
def _me(u):
    return dict(user_json(u), permissions=sorted(p for p, roles in PERMISSIONS.items() if u.role in roles),
                demo_limits=bool(u.is_demo))


@bp.get("/auth/me")
def me():
    return jsonify(user=_me(g._login_user), expires_at=_iso(g.api_token.expires_at))


@bp.post("/auth/logout")
def logout():
    g.api_token.revoked_at = utcnow()
    log_action("logout", "user", g._login_user.id, "api")
    db.session.commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------ missions
@bp.get("/missions")
def missions():
    _require("missions.view")
    return jsonify(items=[mission_json(m) for m in Mission.query.order_by(Mission.code)])


@bp.post("/missions")
@bp.put("/missions/<int:mission_id>")
def mission_save(mission_id=None):
    _require("missions.manage")
    m = db.get_or_404(Mission, mission_id) if mission_id else None
    data = request.get_json(silent=True) or {}
    form = _form(MissionForm, data, obj=m)
    if not form.validate():
        return _err(422, "Validation failed.", fields=_form_errors(form))
    clash = Mission.query.filter(Mission.code == form.code.data, Mission.id != (m.id if m else 0)).first()
    if clash:
        return _err(422, "Validation failed.", fields={"code": ["Mission code already exists."]})
    new = m is None
    m = m or Mission(is_synthetic=False)
    form.populate_obj(m)
    db.session.add(m)
    db.session.flush()
    log_action("create" if new else "update", "mission", m.id, f"{m.code} (api)")
    db.session.commit()
    return jsonify(item=mission_json(m)), (201 if new else 200)


@bp.delete("/missions/<int:mission_id>")
def mission_delete(mission_id):
    _require("missions.manage")
    m = db.get_or_404(Mission, mission_id)
    if m.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    if m.astronauts:
        return _err(409, f"Mission {m.code} still has {len(m.astronauts)} assigned astronaut(s).")
    log_action("delete", "mission", m.id, f"{m.code} (api)")
    db.session.delete(m)
    db.session.commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------ astronauts
@bp.get("/astronauts")
def astronauts():
    _require("astronauts.view")
    return jsonify(items=[astronaut_json(a) for a in Astronaut.query.order_by(Astronaut.code)])


@bp.get("/astronauts/<int:astronaut_id>")
def astronaut_get(astronaut_id):
    _require("astronauts.view")
    return jsonify(item=astronaut_json(db.get_or_404(Astronaut, astronaut_id)))


@bp.post("/astronauts")
@bp.put("/astronauts/<int:astronaut_id>")
def astronaut_save(astronaut_id=None):
    _require("astronauts.manage")
    a = db.get_or_404(Astronaut, astronaut_id) if astronaut_id else None
    data = dict(request.get_json(silent=True) or {})
    data.setdefault("mission_id", 0)
    form = _form(AstronautForm, data, obj=a)
    form.mission_id.choices = [(0, "—")] + [(m.id, m.code) for m in Mission.query]
    if not form.validate():
        return _err(422, "Validation failed.", fields=_form_errors(form))
    clash = Astronaut.query.filter(Astronaut.code == form.code.data, Astronaut.id != (a.id if a else 0)).first()
    if clash:
        return _err(422, "Validation failed.", fields={"code": ["Astronaut code already exists."]})
    new = a is None
    a = a or Astronaut(is_synthetic=False)
    form.populate_obj(a)
    a.mission_id = form.mission_id.data or None
    db.session.add(a)
    db.session.flush()
    log_action("create" if new else "update", "astronaut", a.id, f"{a.code} (api)")
    db.session.commit()
    return jsonify(item=astronaut_json(a)), (201 if new else 200)


@bp.delete("/astronauts/<int:astronaut_id>")
def astronaut_delete(astronaut_id):
    _require("astronauts.manage")
    a = db.get_or_404(Astronaut, astronaut_id)
    if a.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    open_priority = sum(1 for al in a.alerts if al.level == "priority" and al.status == "open")
    if open_priority and request.args.get("confirm") != "yes":
        return _err(409, "This astronaut has open priority alerts. Confirm the deletion explicitly.", open_priority=open_priority)
    log_action("delete", "astronaut", a.id, f"{a.code}: {len(a.measurements)} measurements removed (api)")
    db.session.delete(a)
    db.session.commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------ measurements
@bp.get("/measurements")
def measurements():
    _require("measurements.view")
    q = HealthMeasurement.query
    if request.args.get("astronaut_id", type=int):
        q = q.filter(HealthMeasurement.astronaut_id == request.args.get("astronaut_id", type=int))
    d_from, d_to = _parse_dt(request.args.get("from")), _parse_dt(request.args.get("to"))
    if d_from is False or d_to is False:
        return _err(400, "Invalid date filter (use ISO 8601, e.g. 2026-11-01).")
    if d_from:
        q = q.filter(HealthMeasurement.measured_at >= d_from)
    if d_to:
        q = q.filter(HealthMeasurement.measured_at < (d_to + timedelta(days=1) if len(request.args["to"]) == 10 else d_to))
    total = q.count()
    limit = max(1, min(request.args.get("limit", 500, type=int), 2000))
    offset = max(0, request.args.get("offset", 0, type=int))
    items = q.order_by(HealthMeasurement.measured_at.desc()).offset(offset).limit(limit).all()
    return jsonify(items=[measurement_json(m) for m in items], total=total, limit=limit, offset=offset)


def _measurement_payload(data, m=None):
    data = dict(data or {})
    dt = _parse_dt(data.get("measured_at")) if data.get("measured_at") else (m.measured_at if m else utcnow())
    if dt is False:
        return None, _err(422, "Validation failed.", fields={"measured_at": ["Invalid date/time."]})
    if dt > utcnow() + timedelta(minutes=5):
        return None, _err(422, "Validation failed.", fields={"measured_at": ["Time cannot be in the future."]})
    data["measured_at"] = dt.strftime("%Y-%m-%dT%H:%M")
    if m:  # partial update keeps existing values unless provided
        for f in HealthMeasurement.VITAL_FIELDS + ("notes",):
            if f not in data:
                data[f] = getattr(m, f)
        data.setdefault("astronaut_id", m.astronaut_id)
    form = _form(MeasurementForm, data, obj=None)
    form.astronaut_id.choices = [(a.id, a.code) for a in Astronaut.query]
    if not form.validate():
        return None, _err(422, "Validation failed.", fields=_form_errors(form))
    return form, None


@bp.post("/measurements")
def measurement_create():
    _require("measurements.create")
    data = request.get_json(silent=True) or {}
    form, err = _measurement_payload(data)
    if err:
        return err
    m = HealthMeasurement(recorded_by_id=g._login_user.id, source=str(data.get("source") or "manual")[:40], is_synthetic=False)
    form.populate_obj(m)
    db.session.add(m)
    db.session.flush()
    alerts = generate_alerts(m)
    log_action("create", "measurement", m.id, f"astronaut {m.astronaut_id}; {len(alerts)} alert(s) (api)")
    db.session.commit()
    return jsonify(item=measurement_json(m), alerts=[alert_json(a) for a in alerts]), 201


@bp.put("/measurements/<int:measurement_id>")
def measurement_update(measurement_id):
    _require("measurements.edit")
    m = db.get_or_404(HealthMeasurement, measurement_id)
    form, err = _measurement_payload(request.get_json(silent=True) or {}, m)
    if err:
        return err
    form.populate_obj(m)
    db.session.flush()
    alerts = generate_alerts(m)
    log_action("update", "measurement", m.id, f"astronaut {m.astronaut_id}; {len(alerts)} alert(s) (api)")
    db.session.commit()
    return jsonify(item=measurement_json(m), alerts=[alert_json(a) for a in alerts])


@bp.delete("/measurements/<int:measurement_id>")
def measurement_delete(measurement_id):
    _require("measurements.delete")
    m = db.get_or_404(HealthMeasurement, measurement_id)
    if m.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    HealthAlert.query.filter_by(measurement_id=m.id, status="open").delete()
    log_action("delete", "measurement", m.id, f"astronaut {m.astronaut_id} (api)")
    db.session.delete(m)
    db.session.commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------ alerts
@bp.get("/alerts")
def alerts():
    _require("alerts.view")
    q = HealthAlert.query
    if request.args.get("astronaut_id", type=int):
        q = q.filter(HealthAlert.astronaut_id == request.args.get("astronaut_id", type=int))
    if request.args.get("status") in ("open", "acknowledged", "resolved"):
        q = q.filter(HealthAlert.status == request.args["status"])
    if request.args.get("level") in ("info", "followup", "priority"):
        q = q.filter(HealthAlert.level == request.args["level"])
    items = q.order_by(HealthAlert.created_at.desc()).limit(500).all()
    return jsonify(items=[alert_json(a) for a in items])


@bp.patch("/alerts/<int:alert_id>")
def alert_review(alert_id):
    _require("alerts.manage")
    a = db.get_or_404(HealthAlert, alert_id)
    form = _form(AlertReviewForm, request.get_json(silent=True) or {})
    if not form.validate():
        return _err(422, "Validation failed.", fields=_form_errors(form))
    a.status, a.review_notes = form.status.data, form.review_notes.data
    a.reviewed_by_id, a.reviewed_at = g._login_user.id, utcnow()
    log_action("update", "alert", a.id, f"status={a.status} (api)")
    db.session.commit()
    return jsonify(item=alert_json(a))


# ------------------------------------------------------------------ users / audit / reports
@bp.get("/users")
def users():
    _require("users.manage")
    return jsonify(items=[user_json(u) for u in User.query.order_by(User.role, User.full_name)], read_only=is_demo_user())


@bp.post("/users")
@bp.put("/users/<int:user_id>")
def user_save(user_id=None):
    _require("users.manage")
    demo_forbidden("User management is read-only for public demo accounts.")
    u = db.get_or_404(User, user_id) if user_id else None
    form = _form(UserForm, request.get_json(silent=True) or {}, obj=u)
    if not form.validate():
        return _err(422, "Validation failed.", fields=_form_errors(form))
    email = form.email.data.strip().lower()
    if User.query.filter(User.email == email, User.id != (u.id if u else 0)).first():
        return _err(422, "Validation failed.", fields={"email": ["Email already in use."]})
    if not u and not form.password.data:
        return _err(422, "Validation failed.", fields={"password": ["A password is required for new users."]})
    if u and u.id == g._login_user.id and (form.role.data != "admin" or not form.is_active_account.data):
        return _err(422, "Validation failed.", fields={"role": ["You cannot remove your own administrator access."]})
    new = u is None
    u = u or User()
    u.full_name, u.email, u.role, u.is_active_account = form.full_name.data.strip(), email, form.role.data, form.is_active_account.data
    if form.password.data:
        u.set_password(form.password.data)
    db.session.add(u)
    db.session.flush()
    log_action("create" if new else "update", "user", u.id, f"role={u.role} (api)")
    db.session.commit()
    return jsonify(item=user_json(u)), (201 if new else 200)


@bp.delete("/users/<int:user_id>")
def user_delete(user_id):
    _require("users.manage")
    demo_forbidden("User management is read-only for public demo accounts.")
    u = db.get_or_404(User, user_id)
    if u.id == g._login_user.id:
        return _err(409, "You cannot delete your own account.")
    if u.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        return _err(409, "At least one administrator must remain.")
    log_action("delete", "user", u.id, f"{u.email} (api)")
    db.session.delete(u)
    db.session.commit()
    return jsonify(ok=True)


@bp.get("/audit")
def audit():
    _require("audit.view")
    demo = is_demo_user()
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(items=[dict(created_at=_iso(r.created_at), user=mask_email(r.user.email) if r.user else None,
                               action=r.action, entity=r.entity, entity_id=r.entity_id,
                               details=(mask_email(r.details.replace("api: ", "")) if demo and r.action == "login_failed" else r.details),
                               ip_address=("hidden" if r.ip_address else None) if demo else r.ip_address) for r in rows])


@bp.get("/reports/summary")
def report_summary():
    _require("reports.view")
    open_alerts = HealthAlert.query.filter_by(status="open")
    return jsonify(astronauts=Astronaut.query.count(), missions=Mission.query.count(),
                   measurements=HealthMeasurement.query.count(),
                   open_alerts={lvl: open_alerts.filter_by(level=lvl).count() for lvl in ("priority", "followup", "info")},
                   by_astronaut=[dict(code=a.code, overall_status=astronaut_json(a)["overall_status"],
                                      measurements=len(a.measurements)) for a in Astronaut.query.order_by(Astronaut.code)])
