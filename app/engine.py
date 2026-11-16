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
    "AASM_SLEEP": "AASM/SRS consensus (Watson et al., Sleep 2015) — adults should sleep 7 or more hours per night on a regular basis.",
    "NASA_EXERCISE": "NASA — ISS crew members exercise about 2 hours per day (resistive + aerobic) to counter bone and muscle loss.",
    "SAMN_PERELLI": "Samn-Perelli 7-point fatigue scale (Samn & Perelli, USAF SAM 1982); scores of 5–7 indicate moderate-to-extreme fatigue.",
    "ADA_GLUCOSE": "American Diabetes Association Standards of Care — Level 1 hypoglycemia <70 mg/dL; Level 2 <54 mg/dL; normal fasting glucose 70–99 mg/dL.",
    "ENGINE": "ASTRA VITAL engine convention (engineering rule, not a clinical threshold).",
}

METRICS = {
    "heart_rate": dict(label="Heart rate", unit="bpm", ref=(60, 100), src="AHA_HR", sd_floor=3, worse="both", system="Cardiovascular", hazards="Gravity fields, Isolation"),
    "systolic_bp": dict(label="Systolic blood pressure", unit="mmHg", ref=(90, 120), src="ACC_AHA_BP", sd_floor=4, worse="up", system="Cardiovascular", hazards="Gravity fields, Hostile/closed environments"),
    "spo2": dict(label="Oxygen saturation", unit="%", ref=(95, 100), src="SPO2", sd_floor=0.7, worse="down", system="Respiratory / general", hazards="Hostile/closed environments"),
    "temperature": dict(label="Body temperature", unit="°C", ref=(36.1, 37.2), src="CDC_FEVER", sd_floor=0.2, worse="up", system="Immune", hazards="Hostile/closed environments, Radiation"),
    "respiratory_rate": dict(label="Respiratory rate", unit="breaths/min", ref=(12, 20), src="RR", sd_floor=1.5, worse="both", system="Respiratory / general", hazards="Hostile/closed environments"),
    # indicators of the original ASTRA VITAL app (src/engine.js)
    "sleep_hours": dict(label="Sleep duration", unit="h", ref=(7, 9), src="AASM_SLEEP", sd_floor=0.4, worse="down", system="Nervous / behavioral", hazards="Isolation, Hostile/closed environments"),
    "exercise_min": dict(label="Exercise completed", unit="min", ref=(120, 180), src="NASA_EXERCISE", sd_floor=10, worse="down", system="Musculoskeletal", hazards="Gravity fields"),
    "fatigue": dict(label="Fatigue (Samn-Perelli 1–7)", unit="score", ref=(1, 4), src="SAMN_PERELLI", sd_floor=0.8, worse="up", system="Nervous / behavioral", hazards="Isolation, Hostile/closed environments"),
    "mood": dict(label="Mood / well-being (1–5)", unit="score", ref=(3, 5), src="ENGINE", sd_floor=0.5, worse="down", system="Nervous / behavioral", hazards="Isolation, Distance from Earth"),
    "glucose": dict(label="Blood glucose", unit="mg/dL", ref=(70, 99), src="ADA_GLUCOSE", sd_floor=6, worse="both", system="General", hazards="Gravity fields, Hostile/closed environments"),
}

ACTIONS = {
    "heart_rate": "Re-measure after 5 minutes of seated rest, away from exercise and caffeine. Note symptoms (palpitations, dizziness, chest discomfort).",
    "systolic_bp": "Re-measure after 5 minutes seated, back supported, same arm, cuff at heart level. Take 2 readings 1 minute apart and record the average.",
    "spo2": "Re-measure: warm the finger, keep still, check sensor placement and cabin O2/CO2 readouts. If confirmed below 90% or with breathlessness/confusion, follow the onboard emergency medical checklist.",
    "temperature": "Re-measure in 15 minutes, record symptoms, hydrate and rest. Follow the onboard checklist for fever and inform the crew medical officer.",
    "respiratory_rate": "Count breaths for a full 60 seconds at rest. If abnormal together with low SpO2 or breathlessness, follow the onboard medical checklist.",
    "sleep_hours": "Protect the next sleep period: dim light 1 h before, eye mask/earplugs, avoid caffeine late in the day. Discuss persistent short sleep at the next medical conference.",
    "exercise_min": "Complete the prescribed resistive and aerobic sessions; if workload prevents it, report it so the exercise plan can be adjusted.",
    "fatigue": "Plan rest if operations allow, avoid critical tasks while very tired, and re-check after sleep. Report persistent high fatigue.",
    "mood": "Use the crew support resources (private family/psychological conferences) and talk with the crew medical officer if low mood persists.",
    "glucose": "Re-measure with the onboard glucometer. If low, take fast-acting carbohydrate per the onboard checklist and re-check in 15 minutes.",
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
    return f"{v:.1f}" if metric in ("spo2", "temperature", "sleep_hours") else f"{int(round(v))}"


def reference_findings(m, history=()):
    """Rules on documented reference thresholds (same rules as the original src/engine.js).
    history: earlier measurements of the same astronaut, oldest first (used by the multi-day sleep/exercise rules)."""
    out = []
    g = lambda obj, k: getattr(obj, k, None)
    glu, fat, slp, exe = g(m, "glucose"), g(m, "fatigue"), g(m, "sleep_hours"), g(m, "exercise_min")
    if glu is not None:
        if glu < 54:
            out.append(("priority", "glucose", f"Glucose {glu} mg/dL is Level 2 hypoglycemia (<54)."))
        elif glu < 70:
            out.append(("followup", "glucose", f"Glucose {glu} mg/dL is Level 1 hypoglycemia (<70)."))
    if fat is not None and fat >= 5:
        out.append(("followup", "fatigue", f"Samn-Perelli score {fat} indicates moderate-to-extreme fatigue."))
    if slp is not None:
        last3 = [v for v in (g(h, "sleep_hours") for h in history) if v is not None][-2:] + [slp]
        if len(last3) == 3 and all(v < 7 for v in last3):
            out.append(("followup", "sleep_hours", f"The last 3 sleep periods were all under 7 h ({', '.join(f'{v:.1f}' for v in last3)} h). Persistent short sleep is a known spaceflight issue."))
        elif slp < 7:
            out.append(("info", "sleep_hours", f"Last sleep period {slp:.1f} h is under the 7 h adult recommendation."))
    if exe is not None:
        last3 = [v for v in (g(h, "exercise_min") for h in history) if v is not None][-2:] + [exe]
        if len(last3) == 3 and all(v < 120 for v in last3):
            out.append(("followup", "exercise_min", f"Exercise was below the ~2 h/day prescription on 3 consecutive days ({', '.join(str(v) for v in last3)} min)."))
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
    for level, metric, why in reference_findings(measurement, history):
        findings.setdefault(metric, []).append(("reference", level, why))
    for metric, meta in METRICS.items():
        v = getattr(measurement, metric, None)
        if v is None:
            continue
        hist = [getattr(h, metric, None) for h in history if getattr(h, metric, None) is not None]
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
