"""Synthetic demonstration data (clearly flagged is_synthetic=True). Fictional astronauts — no real people."""
import random
from datetime import date, timedelta
from .extensions import db
from .models import Mission, Astronaut, HealthMeasurement, utcnow
from .services import generate_alerts


def seed_demo(days=21):
    if Astronaut.query.filter_by(is_synthetic=True).count():
        return 0
    rnd = random.Random(2026)
    today = date.today()
    m1 = Mission(code="AV-ANALOG-180", name="ASTRA-180 long-duration analog (fictional)", environment="spacecraft",
                 start_date=today - timedelta(days=41), duration_days=180, status="active", is_synthetic=True,
                 description="Fictional demonstration mission for the academic edition. Not a real mission.")
    m2 = Mission(code="AV-LUNAR-30", name="Lunar surface rotation (fictional)", environment="moon",
                 start_date=today + timedelta(days=60), duration_days=30, status="planned", is_synthetic=True,
                 description="Fictional planned mission used to demonstrate mission management.")
    db.session.add_all([m1, m2])
    db.session.flush()
    crew = [("AV-DEMO-01", "Demo Crew Member Alpha (fictional)", 41, "Flight Engineer", "drift"),
            ("AV-DEMO-02", "Demo Crew Member Bravo (fictional)", 36, "Commander", "stable"),
            ("AV-DEMO-03", "Demo Crew Member Charlie (fictional)", 45, "Mission Specialist", "fever"),
            ("AV-DEMO-04", "Demo Crew Member Delta (fictional)", 33, "Medical Officer", "stable")]
    n = 0
    for code, name, age, role, scenario in crew:
        a = Astronaut(code=code, full_name=name, demo_age=age, role_on_board=role, mission_id=m1.id, status="active",
                      is_synthetic=True, notes="Synthetic demonstration profile. Not a real person.")
        db.session.add(a)
        db.session.flush()
        g = lambda mu, s: mu + rnd.gauss(0, s)
        start = utcnow().replace(hour=7, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
        for d in range(days):
            if scenario == "drift" and d == days - 5:
                continue  # missed day
            late = max(0, d - (days - 8)) if scenario == "drift" else 0
            hr = round(g(68 + late * 2.2, 2.5))
            sbp, dbp = round(g(116 + late * 2.2, 3.5)), round(g(74 + late * 1.3, 2.5))
            spo2 = round(min(100, g(97.6, 0.5)), 1)
            temp = round(g(36.6, 0.12), 1)
            rr = round(g(14, 1))
            if scenario == "drift" and d == days - 1:
                spo2 = 89.0
            if scenario == "fever" and d >= days - 2:
                temp, hr, rr = (38.3 if d == days - 1 else 37.6), hr + 12, rr + 4
            # indicators of the original ASTRA VITAL app (same drift scenario as demoRecords() in src/app.js)
            sleep = round(max(3.5, g(6.9 - late * 0.27 if scenario == "drift" else 7.3, 0.3)), 1)
            fatigue = int(min(7, max(1, round(g(2.6 + late * 0.45, 0.6)))))
            mood = int(min(5, max(1, round(g(4.2 - late * 0.17, 0.4)))))
            exercise = int(round(max(0, g(85 if (scenario == "drift" and d >= days - 4) else 126, 9))))
            glucose = int(round(g(88, 5))) if d % 5 == 0 else None
            m = HealthMeasurement(astronaut_id=a.id, measured_at=start + timedelta(days=d, minutes=rnd.randint(0, 40)),
                                  heart_rate=hr, systolic_bp=sbp, diastolic_bp=max(40, min(dbp, sbp - 15)), spo2=spo2,
                                  temperature=temp, respiratory_rate=rr, sleep_hours=sleep, exercise_min=exercise,
                                  fatigue=fatigue, mood=mood, glucose=glucose, source="synthetic_demo", is_synthetic=True,
                                  notes="SYNTHETIC demo measurement")
            db.session.add(m)
            db.session.flush()
            generate_alerts(m)
            n += 1
    db.session.commit()
    return n
