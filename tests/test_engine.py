from types import SimpleNamespace as M
from datetime import datetime, timedelta
from app.engine import analyze_measurement, overall_status

T = datetime(2026, 11, 10, 8)


def m(**kw):
    base = dict(heart_rate=None, systolic_bp=None, diastolic_bp=None, spo2=None, temperature=None, respiratory_rate=None, measured_at=T)
    base.update(kw)
    return M(**base)


def test_spo2_below_90_is_priority():
    a = analyze_measurement(m(spo2=88), [])
    assert a[0].level == "priority" and a[0].metric == "spo2"


def test_hypertensive_crisis_priority_and_stage2_followup():
    assert analyze_measurement(m(systolic_bp=185, diastolic_bp=100), [])[0].level == "priority"
    assert analyze_measurement(m(systolic_bp=145, diastolic_bp=85), [])[0].level == "followup"


def test_normal_values_no_alerts():
    assert analyze_measurement(m(heart_rate=72, systolic_bp=115, diastolic_bp=75, spo2=98, temperature=36.6, respiratory_rate=14), []) == []


def test_consolidation_one_alert_per_metric():
    hist = [m(heart_rate=v, measured_at=T - timedelta(days=9 - i)) for i, v in enumerate([62, 63, 62, 61, 63, 62, 62])]
    a = analyze_measurement(m(heart_rate=110), hist)
    assert len(a) == 1 and a[0].rule == "reference+baseline"


def test_overall_status():
    assert overall_status({"followup", "priority"}) == "priority" and overall_status(set()) == "nominal"
