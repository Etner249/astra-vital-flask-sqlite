"""CRUD blueprints: astronauts, missions, measurements, alerts, users."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .decorators import permission_required, can
from .forms import AstronautForm, MissionForm, MeasurementForm, AlertReviewForm, UserForm, DeleteForm
from .models import Astronaut, Mission, HealthMeasurement, HealthAlert, User, utcnow
from .services import log_action, generate_alerts
from .engine import overall_status
from .demo import demo_forbidden, is_demo_user

BASELINE_MSG = ("Las cuentas públicas de demostración no pueden eliminar los datos sintéticos de referencia. "
                "Crea un registro nuevo y elimínalo para probar la operación.")

bp = Blueprint("crud", __name__)


def _mission_choices():
    return [(0, "— No mission —")] + [(m.id, f"{m.code} · {m.name}") for m in Mission.query.order_by(Mission.code)]


def _astronaut_choices():
    return [(a.id, f"{a.code} · {a.full_name}") for a in Astronaut.query.order_by(Astronaut.code)]


# ---------------------------------------------------------------- Astronauts
@bp.route("/astronauts")
@permission_required("astronauts.view")
def astronauts():
    q = request.args.get("q", "").strip()
    query = Astronaut.query
    if q:
        like = f"%{q}%"
        query = query.filter((Astronaut.code.ilike(like)) | (Astronaut.full_name.ilike(like)))
    items = query.order_by(Astronaut.code).all()
    status = {a.id: overall_status({al.level for al in a.alerts if al.status != "resolved"}) for a in items}
    return render_template("astronauts/list.html", items=items, q=q, status=status, delete_form=DeleteForm())


@bp.route("/astronauts/new", methods=["GET", "POST"])
@permission_required("astronauts.manage")
def astronaut_new():
    form = AstronautForm()
    form.mission_id.choices = _mission_choices()
    if form.validate_on_submit():
        a = Astronaut()
        form.populate_obj(a)
        a.code = a.code.upper()
        a.mission_id = form.mission_id.data or None
        db.session.add(a)
        try:
            db.session.flush()
            log_action("create", "astronaut", a.id, a.code)
            db.session.commit()
            flash(f"Astronaut {a.code} registered.", "success")
            return redirect(url_for("crud.astronaut_detail", astronaut_id=a.id))
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append("This astronaut code already exists.")
    return render_template("astronauts/form.html", form=form, title="Register astronaut")


@bp.route("/astronauts/<int:astronaut_id>")
@permission_required("astronauts.view")
def astronaut_detail(astronaut_id):
    a = db.get_or_404(Astronaut, astronaut_id)
    ms = HealthMeasurement.query.filter_by(astronaut_id=a.id).order_by(HealthMeasurement.measured_at.asc()).all()
    series = {k: [[m.measured_at.isoformat(), getattr(m, k)] for m in ms if getattr(m, k) is not None]
              for k in ("heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature", "respiratory_rate")}
    status = overall_status({al.level for al in a.alerts if al.status != "resolved"})
    return render_template("astronauts/detail.html", a=a, measurements=list(reversed(ms)), series=series,
                           status=status, delete_form=DeleteForm())


@bp.route("/astronauts/<int:astronaut_id>/edit", methods=["GET", "POST"])
@permission_required("astronauts.manage")
def astronaut_edit(astronaut_id):
    a = db.get_or_404(Astronaut, astronaut_id)
    form = AstronautForm(obj=a)
    form.mission_id.choices = _mission_choices()
    if request.method == "GET":
        form.mission_id.data = a.mission_id or 0
    if form.validate_on_submit():
        form.populate_obj(a)
        a.code = a.code.upper()
        a.mission_id = form.mission_id.data or None
        try:
            log_action("update", "astronaut", a.id, a.code)
            db.session.commit()
            flash(f"Astronaut {a.code} updated.", "success")
            return redirect(url_for("crud.astronaut_detail", astronaut_id=a.id))
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append("This astronaut code already exists.")
    return render_template("astronauts/form.html", form=form, title=f"Edit {a.code}", a=a)


@bp.route("/astronauts/<int:astronaut_id>/delete", methods=["GET", "POST"])
@permission_required("astronauts.manage")
def astronaut_delete(astronaut_id):
    a = db.get_or_404(Astronaut, astronaut_id)
    if a.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    form = DeleteForm()
    open_priority = sum(1 for al in a.alerts if al.level == "priority" and al.status == "open")
    if request.method == "POST":
        if not form.validate_on_submit():
            abort(400)
        if open_priority and request.form.get("confirm_open_alerts") != "yes":
            flash("This astronaut has open priority alerts. Review them or confirm the deletion explicitly.", "warning")
            return redirect(url_for("crud.astronaut_delete", astronaut_id=a.id))
        code = a.code
        log_action("delete", "astronaut", a.id, f"{code}: {len(a.measurements)} measurements and {len(a.alerts)} alerts removed")
        db.session.delete(a)  # ORM cascade removes measurements and alerts
        db.session.commit()
        flash(f"Astronaut {code} and related records deleted.", "success")
        return redirect(url_for("crud.astronauts"))
    return render_template("astronauts/delete.html", a=a, form=form, open_priority=open_priority)


# ---------------------------------------------------------------- Missions
@bp.route("/missions")
@permission_required("missions.view")
def missions():
    return render_template("missions/list.html", items=Mission.query.order_by(Mission.start_date.desc()).all(), delete_form=DeleteForm())


@bp.route("/missions/new", methods=["GET", "POST"])
@bp.route("/missions/<int:mission_id>/edit", methods=["GET", "POST"])
@permission_required("missions.manage")
def mission_form(mission_id=None):
    m = db.get_or_404(Mission, mission_id) if mission_id else None
    form = MissionForm(obj=m)
    if form.validate_on_submit():
        new = m is None
        m = m or Mission()
        form.populate_obj(m)
        m.code = m.code.upper()
        db.session.add(m)
        try:
            db.session.flush()
            log_action("create" if new else "update", "mission", m.id, m.code)
            db.session.commit()
            flash(f"Mission {m.code} saved.", "success")
            return redirect(url_for("crud.missions"))
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append("This mission code already exists.")
    return render_template("missions/form.html", form=form, m=m)


@bp.route("/missions/<int:mission_id>/delete", methods=["POST"])
@permission_required("missions.manage")
def mission_delete(mission_id):
    m = db.get_or_404(Mission, mission_id)
    if m.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    if not DeleteForm().validate_on_submit():
        abort(400)
    if m.astronauts:
        flash(f"Mission {m.code} still has {len(m.astronauts)} assigned astronaut(s). Reassign them before deleting.", "warning")
        return redirect(url_for("crud.missions"))
    log_action("delete", "mission", m.id, m.code)
    db.session.delete(m)
    db.session.commit()
    flash(f"Mission {m.code} deleted.", "success")
    return redirect(url_for("crud.missions"))


# ---------------------------------------------------------------- Measurements
@bp.route("/measurements")
@permission_required("measurements.view")
def measurements():
    query = HealthMeasurement.query.join(Astronaut)
    astro = request.args.get("astronaut_id", type=int)
    d_from = request.args.get("from", "")
    d_to = request.args.get("to", "")
    if astro:
        query = query.filter(HealthMeasurement.astronaut_id == astro)
    try:
        if d_from:
            query = query.filter(HealthMeasurement.measured_at >= datetime.strptime(d_from, "%Y-%m-%d"))
        if d_to:
            query = query.filter(HealthMeasurement.measured_at < datetime.strptime(d_to, "%Y-%m-%d") + timedelta(days=1))
    except ValueError:
        flash("Invalid date filter (use YYYY-MM-DD).", "warning")
    page = request.args.get("page", 1, type=int)
    pag = query.order_by(HealthMeasurement.measured_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template("measurements/list.html", pag=pag, astronauts=Astronaut.query.order_by(Astronaut.code).all(),
                           astro=astro, d_from=d_from, d_to=d_to, delete_form=DeleteForm())


@bp.route("/measurements/new", methods=["GET", "POST"])
@bp.route("/measurements/<int:measurement_id>/edit", methods=["GET", "POST"])
@permission_required("measurements.create")
def measurement_form(measurement_id=None):
    m = db.get_or_404(HealthMeasurement, measurement_id) if measurement_id else None
    if m and not can("measurements.edit"):
        abort(403)
    form = MeasurementForm(obj=m)
    form.astronaut_id.choices = _astronaut_choices()
    if not form.astronaut_id.choices:
        flash("Register an astronaut first.", "warning")
        return redirect(url_for("crud.astronauts"))
    if request.method == "GET" and not m:
        form.measured_at.data = utcnow().replace(second=0, microsecond=0)
        if request.args.get("astronaut_id", type=int):
            form.astronaut_id.data = request.args.get("astronaut_id", type=int)
    if form.validate_on_submit():
        new = m is None
        m = m or HealthMeasurement(recorded_by_id=current_user.id, source="manual", is_synthetic=False)
        form.populate_obj(m)
        db.session.add(m)
        db.session.flush()
        alerts = generate_alerts(m)
        log_action("create" if new else "update", "measurement", m.id, f"astronaut {m.astronaut_id}; {len(alerts)} alert(s)")
        db.session.commit()
        msg = f"Measurement saved. {len(alerts)} alert(s) generated." if alerts else "Measurement saved. No alerts for this measurement."
        flash(msg, "warning" if any(a.level == "priority" for a in alerts) else "success")
        return redirect(url_for("crud.astronaut_detail", astronaut_id=m.astronaut_id))
    return render_template("measurements/form.html", form=form, m=m)


@bp.route("/measurements/<int:measurement_id>/delete", methods=["POST"])
@permission_required("measurements.delete")
def measurement_delete(measurement_id):
    m = db.get_or_404(HealthMeasurement, measurement_id)
    if m.is_synthetic:
        demo_forbidden(BASELINE_MSG)
    if not DeleteForm().validate_on_submit():
        abort(400)
    HealthAlert.query.filter_by(measurement_id=m.id, status="open").delete()
    log_action("delete", "measurement", m.id, f"astronaut {m.astronaut_id}")
    aid = m.astronaut_id
    db.session.delete(m)
    db.session.commit()
    flash("Measurement deleted (its open alerts were removed; reviewed alerts are kept for the record).", "success")
    nxt = request.form.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("crud.astronaut_detail", astronaut_id=aid))


# ---------------------------------------------------------------- Alerts
@bp.route("/alerts")
@permission_required("alerts.view")
def alerts():
    status = request.args.get("status", "open")
    level = request.args.get("level", "")
    query = HealthAlert.query
    if status in ("open", "acknowledged", "resolved"):
        query = query.filter_by(status=status)
    if level in ("priority", "followup", "info"):
        query = query.filter_by(level=level)
    order = db.case({"priority": 0, "followup": 1, "info": 2}, value=HealthAlert.level)
    items = query.order_by(order, HealthAlert.created_at.desc()).limit(200).all()
    return render_template("alerts/list.html", items=items, status=status, level=level)


@bp.route("/alerts/<int:alert_id>", methods=["GET", "POST"])
@permission_required("alerts.view")
def alert_detail(alert_id):
    a = db.get_or_404(HealthAlert, alert_id)
    form = AlertReviewForm(obj=a)
    if request.method == "POST":
        if not can("alerts.manage"):
            abort(403)
        if form.validate_on_submit():
            a.status = form.status.data
            a.review_notes = form.review_notes.data
            a.reviewed_by_id = current_user.id
            a.reviewed_at = utcnow()
            log_action("update", "alert", a.id, f"status={a.status}")
            db.session.commit()
            flash("Alert updated.", "success")
            return redirect(url_for("crud.alert_detail", alert_id=a.id))
    return render_template("alerts/detail.html", a=a, form=form)


@bp.route("/alerts/regenerate/<int:measurement_id>", methods=["POST"])
@permission_required("alerts.manage")
def alert_regenerate(measurement_id):
    m = db.get_or_404(HealthMeasurement, measurement_id)
    if not DeleteForm().validate_on_submit():
        abort(400)
    created = generate_alerts(m)
    log_action("create", "alert", None, f"regenerated for measurement {m.id}: {len(created)}")
    db.session.commit()
    flash(f"Engine re-run: {len(created)} open alert(s) for this measurement.", "info")
    return redirect(url_for("crud.astronaut_detail", astronaut_id=m.astronaut_id))


# ---------------------------------------------------------------- Users
@bp.route("/users")
@permission_required("users.manage")
def users():
    return render_template("users/list.html", items=User.query.order_by(User.role, User.full_name).all(), delete_form=DeleteForm(),
                           demo=is_demo_user())


@bp.route("/users/new", methods=["GET", "POST"])
@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@permission_required("users.manage")
def user_form(user_id=None):
    demo_forbidden("La gestión de usuarios es de solo lectura para las cuentas públicas de demostración.")
    u = db.get_or_404(User, user_id) if user_id else None
    form = UserForm(obj=u)
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        clash = User.query.filter(User.email == email, User.id != (u.id if u else 0)).first()
        if clash:
            form.email.errors.append("Email already in use.")
        elif not u and not form.password.data:
            form.password.errors.append("A password is required for new users.")
        elif u and u.id == current_user.id and (form.role.data != "admin" or not form.is_active_account.data):
            form.role.errors.append("You cannot remove your own administrator access.")
        else:
            new = u is None
            u = u or User()
            u.full_name, u.email, u.role, u.is_active_account = form.full_name.data.strip(), email, form.role.data, form.is_active_account.data
            if form.password.data:
                u.set_password(form.password.data)
            db.session.add(u)
            db.session.flush()
            log_action("create" if new else "update", "user", u.id, f"role={u.role}")
            db.session.commit()
            flash(f"User {u.email} saved.", "success")
            return redirect(url_for("crud.users"))
    return render_template("users/form.html", form=form, u=u)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@permission_required("users.manage")
def user_delete(user_id):
    demo_forbidden("La gestión de usuarios es de solo lectura para las cuentas públicas de demostración.")
    u = db.get_or_404(User, user_id)
    if not DeleteForm().validate_on_submit():
        abort(400)
    if u.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("crud.users"))
    if u.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        flash("At least one administrator must remain.", "warning")
        return redirect(url_for("crud.users"))
    log_action("delete", "user", u.id, u.email)
    db.session.delete(u)
    db.session.commit()
    flash(f"User {u.email} deleted.", "success")
    return redirect(url_for("crud.users"))
