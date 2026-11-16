"""ASTRA VITAL Health Intelligence Engine — Python port of the original src/engine.js (NASA Space Apps 2026).

Transparent, rule-based (no machine-learning model). Every alert explains what changed, why it matters,
a conservative suggested action and when to contact the medical team. Educational prototype: it does
NOT diagnose and does NOT replace flight surgeons or official protocols.
"""
from dataclasses import dataclass, field
from statistics import mean, pstdev

SOURCES = {
    "AHA_HR": "American Heart Association — normal resting heart rate for adults is 60–100 bpm.",
    "ACC_AHA_BP": "2017 ACC/AHA Hypertension Guideline (Whelton et al., Hypertension 2018) — Stage 2 ≥140 or ≥90 mmHg; hypertensive crisis >180 and/or >120 mmHg.",
    "SPO2": "Typical SpO2 in healthy adults is 95–100%; SpO2 <90% is the commonly used hypoxemia threshold (WHO Pulse Oximetry Training Manual, 2011).",
    "CDC_FEVER": "CDC — a measured temperature of 100.4 °F (38.0 °C) or greater is considered a fever.",
    "RR": "Normal adult resting respiratory rate is about 12–20 breaths per minute (clinical vital-signs references, e.g. Cleveland Clinic).",
    "ENGINE": "ASTRA VITAL engine convention (engineering rule, not a clinical threshold).",
}

METRICS = {
    "heart_rate": dict(label="Heart rate", unit="bpm", ref=(60, 100), src="AHA_HR", sd_floor=3, worse="both", system="Cardiovascular", hazards="Gravity fields, Isolation"),
    "systolic_bp": dict(label="Systolic blood pressure", unit="mmHg", ref=(90, 120), src="ACC_AHA_BP", sd_floor=4, worse="up", system="Cardiovascular", hazards="Gravity fields, Hostile/closed environments"),
    "spo2": dict(label="Oxygen saturation", unit="%", ref=(95, 100), src="SPO2", sd_floor=0.7, worse="down", system="Respiratory / general", hazards="Hostile/closed environments"),
    "temperature": dict(label="Body temperature", unit="°C", ref=(36.1, 37.2), src="CDC_FEVER", sd_floor=0.2, worse="up", system="Immune", hazards="Hostile/closed environments, Radiation"),
    "respiratory_rate": dict(label="Respiratory rate", unit="breaths/min", ref=(12, 20), src="RR", sd_floor=1.5, worse="both", system="Respiratory / general", hazards="Hostile/closed environments"),
}

ACTIONS = {
    "heart_rate": "Re-measure after 5 minutes of seated rest, away from exercise and caffeine. Note symptoms (palpitations, dizziness, chest discomfort).",
    "systolic_bp": "Re-measure after 5 minutes seated, back supported, same arm, cuff at heart level. Take 2 readings 1 minute apart and record the average.",
    "spo2": "Re-measure: warm the finger, keep still, check sensor placement and cabin O2/CO2 readouts. If confirmed below 90% or with breathlessness/confusion, follow the onboard emergency medical checklist.",
    "temperature": "Re-measure in 15 minutes, record symptoms, hydrate and rest. Follow the onboard checklist for fever and inform the crew medical officer.",
    "respiratory_rate": "Count breaths for a full 60 seconds at rest. If abnormal together with low SpO2 or breathlessness, follow the onboard medical checklist.",
}
CONTACT = {
    "priority": "Contact the flight surgeon as soon as possible through the emergency medical channel. If the Earth link is unavailable, follow the onboard medical checklist and inform the crew medical officer.",
    "followup": "Include in the next scheduled Private Medical Conference or next communication window.",
    "info": "No contact needed now — include in the weekly summary.",
}


@dataclass
class AlertDraft:
    level: str
    metric: str
    rule: str
    title: str
    what_changed: str
    why: str
    action: str
    contact: str
    source_ref: str
    evidence: list = field(default_factory=list)


def _fmt(v, metric):
    return f"{v:.1f}" if metric in ("spo2", "temperature") else f"{int(round(v))}"


def reference_findings(m):
    """Rules on documented reference thresholds for a single measurement object (attributes)."""
    out = []
    hr, sbp, dbp, spo2, temp, rr = m.heart_rate, m.systolic_bp, m.diastolic_bp, m.spo2, m.temperature, m.respiratory_rate
    if spo2 is not None:
        if spo2 < 90:
            out.append(("priority", "spo2", f"SpO2 {spo2:.1f}% is below 90%, the commonly used hypoxemia threshold."))
        elif spo2 < 95:
            out.append(("followup", "spo2", f"SpO2 {spo2:.1f}% is below the typical healthy range (95–100%)."))
    if temp is not None and temp >= 38.0:
        out.append(("priority", "temperature", f"Temperature {temp:.1f} °C meets the CDC fever definition (≥38.0 °C)."))
    if sbp is not None and dbp is not None:
        if sbp > 180 or dbp > 120:
            out.append(("priority", "systolic_bp", f"{sbp}/{dbp} mmHg is in the hypertensive-crisis range (>180 and/or >120)."))
        elif sbp >= 140 or dbp >= 90:
            out.append(("followup", "systolic_bp", f"{sbp}/{dbp} mmHg is in the Stage 2 hypertension range (≥140 or ≥90)."))
        elif sbp < 90 or dbp < 60:
            out.append(("followup", "systolic_bp", f"{sbp}/{dbp} mmHg is low; spaceflight can cause orthostatic intolerance after gravity transitions."))
    if hr is not None and (hr < 60 or hr > 100):
        out.append(("followup", "heart_rate", f"Resting heart rate {hr} bpm is outside 60–100 bpm. A low value can be normal in fit individuals; compare with the personal baseline."))
    if rr is not None and (rr < 12 or rr > 20):
        out.append(("followup", "respiratory_rate", f"Respiratory rate {rr} breaths/min is outside the typical adult resting range (12–20)."))
    return out


def baseline(values, metric):
    """Personal baseline from the first 7 valid values (requires ≥5)."""
    if len(values) < 5:
        return None
    first = values[:7]
    return mean(first), max(pstdev(first), METRICS[metric]["sd_floor"]), len(first)


def analyze_measurement(measurement, history):
    """Return consolidated AlertDrafts for one measurement.
    history: earlier measurements of the same astronaut, oldest first (excluding this one)."""
    findings = {}
    for level, metric, why in reference_findings(measurement):
        findings.setdefault(metric, []).append(("reference", level, why))
    for metric, meta in METRICS.items():
        v = getattr(measurement, metric)
        if v is None:
            continue
        hist = [getattr(h, metric) for h in history if getattr(h, metric) is not None]
        b = baseline(hist, metric)
        if not b or len(hist) < b[2]:
            continue
        mu, sd, _ = b
        z = (v - mu) / sd
        bad = abs(z) >= 2 if meta["worse"] == "both" else (z >= 2 if meta["worse"] == "up" else z <= -2)
        if bad:
            findings.setdefault(metric, []).append(("baseline", "followup",
                f"{_fmt(v, metric)} {meta['unit']} vs. personal baseline {_fmt(mu, metric)} ± {sd:.1f} {meta['unit']} (z = {z:.1f}); a ≥2 SD deviation is unusual for this astronaut (engine convention)."))
    drafts = []
    order = {"priority": 0, "followup": 1, "info": 2}
    for metric, items in findings.items():
        items.sort(key=lambda x: (order[x[1]], 0 if x[0] == "reference" else 1))
        rule, level, why = items[0]
        meta = METRICS[metric]
        value = f"{measurement.systolic_bp}/{measurement.diastolic_bp}" if metric == "systolic_bp" else _fmt(getattr(measurement, metric), metric)
        extra = " Supporting evidence: " + " ".join(i[2] for i in items[1:]) if len(items) > 1 else ""
        srcs = {meta["src"] if r == "reference" else "ENGINE" for r, _, _ in items}
        drafts.append(AlertDraft(
            level=level, metric=metric, rule="+".join(i[0] for i in items),
            title=f"{meta['label']}: {'needs attention now' if level == 'priority' else ('outside documented reference' if rule == 'reference' else 'change from personal baseline')}",
            what_changed=f"Measured {value} {meta['unit']} on {measurement.measured_at:%Y-%m-%d %H:%M} UTC.",
            why=why + extra, action=ACTIONS[metric], contact=CONTACT[level],
            source_ref=" | ".join(SOURCES[s] for s in sorted(srcs))))
    drafts.sort(key=lambda d: order[d.level])
    return drafts


def overall_status(levels):
    if "priority" in levels:
        return "priority"
    if "followup" in levels:
        return "followup"
    return "nominal"
