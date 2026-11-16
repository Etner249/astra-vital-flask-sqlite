import csv
import io
import json
from datetime import timedelta
from pathlib import Path
from flask import Blueprint, render_template, Response, redirect, url_for
from sqlalchemy import func
from .extensions import db
from .decorators import permission_required
from .models import Astronaut, Mission, HealthMeasurement, HealthAlert, User, AuditLog, utcnow
from .engine import overall_status, SOURCES

bp = Blueprint("main", __name__)
DATA = Path(__file__).parent / "data"

HAZARDS = [
    ("R", "Space Radiation", "#ff8a5b", "Outside Earth's protective magnetic field and atmosphere, crews are exposed to galactic cosmic rays and solar particle events.",
     ["Increased lifetime cancer risk", "Possible central nervous system effects", "Possible degenerative tissue effects"], "Body temperature and general status are tracked; radiation dose itself requires dosimeters (not measured by this app)."),
    ("I", "Isolation & Confinement", "#b48cff", "Small crews living for months in a confined habitat, far from family, can develop behavioral and team-performance problems.",
     ["Adverse behavioral conditions", "Sleep loss and circadian misalignment", "Reduced team performance"], "Observations field and heart-rate trends; mood and sleep scales exist in the original edition."),
    ("D", "Distance from Earth", "#7aa7ff", "Farther missions mean delayed communication, no quick evacuation and limited onboard medical capability.",
     ["Delayed guidance from flight surgeons", "Crew must assess health autonomously"], "Explainable alerts say what to do and when to contact the medical team."),
    ("G", "Gravity Fields", "#36D6E7", "Weightlessness and partial gravity affect bone, muscle, balance and the cardiovascular system; each gravity transition is a stressor.",
     ["Bone loss of about 1%–1.5% per month (NASA HRP)", "Muscle atrophy", "Orthostatic intolerance", "Sensorimotor changes"], "Heart rate and blood pressure trends."),
    ("E", "Hostile / Closed Environments", "#3ccf91", "The spacecraft is a sealed ecosystem: air quality, CO2, noise, lighting and microbes affect health and immunity.",
     ["Immune dysregulation", "Effects of CO2 and air quality", "Sleep disruption"], "SpO2, respiratory rate and temperature."),
]


@bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@bp.route("/dashboard")
@permission_required("dashboard.view")
def dashboard():
    open_alerts = HealthAlert.query.filter(HealthAlert.status != "resolved")
    counts = dict(db.session.query(HealthAlert.level, func.count()).filter(HealthAlert.status != "resolved").group_by(HealthAlert.level).all())
    stats = {
        "astronauts": Astronaut.query.count(),
        "active_astronauts": Astronaut.query.filter_by(status="active").count(),
        "measurements": HealthMeasurement.query.count(),
        "synthetic": HealthMeasurement.query.filter_by(is_synthetic=True).count(),
        "open_alerts": open_alerts.count(),
        "missions": Mission.query.count(),
        "active_missions": Mission.query.filter_by(status="active").count(),
        "users": User.query.count(),
    }
    status = overall_status(set(counts))
    latest = HealthMeasurement.query.order_by(HealthMeasurement.measured_at.desc()).limit(8).all()
    top_alerts = (open_alerts.order_by(db.case({"priority": 0, "followup": 1, "info": 2}, value=HealthAlert.level),
                                       HealthAlert.created_at.desc()).limit(5).all())
    since = utcnow() - timedelta(days=21)
    ms = HealthMeasurement.query.filter(HealthMeasurement.measured_at >= since).order_by(HealthMeasurement.measured_at).all()
    by_astro = {}
    for m in ms:
        by_astro.setdefault(m.astronaut.code, {"heart_rate": [], "spo2": []})
        if m.heart_rate is not None:
            by_astro[m.astronaut.code]["heart_rate"].append([m.measured_at.isoformat(), m.heart_rate])
        if m.spo2 is not None:
            by_astro[m.astronaut.code]["spo2"].append([m.measured_at.isoformat(), m.spo2])
    per_astro = []
    for a in Astronaut.query.order_by(Astronaut.code):
        lv = {al.level for al in a.alerts if al.status != "resolved"}
        per_astro.append((a, overall_status(lv), sum(1 for al in a.alerts if al.status != "resolved")))
    missions = Mission.query.filter_by(status="active").all()
    return render_template("main/dashboard.html", stats=stats, counts=counts, status=status, latest=latest,
                           top_alerts=top_alerts, chart=json.dumps(by_astro), per_astro=per_astro, missions=missions, now=utcnow())


@bp.route("/risks")
@permission_required("dashboard.view")
def risks():
    return render_template("main/risks.html", hazards=HAZARDS)


@bp.route("/nasa-data")
@permission_required("dashboard.view")
def nasa_data():
    rows = json.loads((DATA / "osdr_i4_subset.json").read_text())
    return render_template("main/nasa.html", rows=rows, rows_json=json.dumps(rows))


@bp.route("/reports")
@permission_required("reports.view")
def reports():
    by_level = dict(db.session.query(HealthAlert.level, func.count()).group_by(HealthAlert.level).all())
    by_status = dict(db.session.query(HealthAlert.status, func.count()).group_by(HealthAlert.status).all())
    per_astro = (db.session.query(Astronaut.code, Astronaut.full_name, func.count(HealthMeasurement.id),
                                  func.avg(HealthMeasurement.heart_rate), func.avg(HealthMeasurement.spo2), func.max(HealthMeasurement.measured_at))
                 .outerjoin(HealthMeasurement).group_by(Astronaut.id).order_by(Astronaut.code).all())
    return render_template("main/reports.html", by_level=by_level, by_status=by_status, per_astro=per_astro, sources=SOURCES)


def _csv(rows, header, name):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.route("/reports/measurements.csv")
@permission_required("reports.view")
def export_measurements():
    ms = HealthMeasurement.query.join(Astronaut).order_by(HealthMeasurement.measured_at).all()
    return _csv([[m.id, m.astronaut.code, m.measured_at.isoformat(), m.heart_rate, m.systolic_bp, m.diastolic_bp, m.spo2, m.temperature,
                  m.respiratory_rate, m.source, "yes" if m.is_synthetic else "no", (m.notes or "").replace("\n", " ")] for m in ms],
                ["id", "astronaut", "measured_at_utc", "heart_rate_bpm", "systolic_mmHg", "diastolic_mmHg", "spo2_pct", "temp_c", "resp_rate", "source", "synthetic", "notes"],
                "astra_vital_measurements.csv")


@bp.route("/reports/alerts.csv")
@permission_required("reports.view")
def export_alerts():
    al = HealthAlert.query.join(Astronaut).order_by(HealthAlert.created_at).all()
    return _csv([[a.id, a.astronaut.code, a.created_at.isoformat(), a.level, a.metric, a.title, a.status, a.why] for a in al],
                ["id", "astronaut", "created_at_utc", "level", "metric", "title", "status", "why"], "astra_vital_alerts.csv")


@bp.route("/audit")
@permission_required("audit.view")
def audit():
    return render_template("main/audit.html", items=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all())


@bp.route("/about")
def about():
    return render_template("main/about.html", sources=SOURCES)
