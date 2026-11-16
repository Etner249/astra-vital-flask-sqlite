# Referencias NASA y científicas

## NASA
1. NASA Space Apps Challenge 2026 — *Create Health Monitoring Software for Astronauts on Space Missions*. https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
2. NASA Human Research Program — *5 Hazards of Human Spaceflight*. https://www.nasa.gov/hrp/hazards/
3. NASA Open Science Data Repository (OSDR) — **OSD-575**: *SpaceX Inspiration4 — Blood serum metabolic panel and immune/cardiac cytokine arrays*. https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
4. NASA OSDR — **OSD-569**: *SpaceX Inspiration4 — Complete blood count*. https://osdr.nasa.gov/bio/repo/data/studies/OSD-569
5. NASA OSDR (portal general). https://osdr.nasa.gov/

Uso en la aplicación: `app/data/osdr_i4_subset.json/.csv` contiene un subconjunto real de estos estudios (4 tripulantes, puntos pre-vuelo y post-vuelo). Son análisis de laboratorio, **no** signos vitales continuos en vuelo, y así se indica en la pantalla "Datos NASA".

## Umbrales clínicos del motor de reglas
6. American Heart Association — rangos de frecuencia cardiaca en reposo (60–100 lpm). https://www.heart.org/
7. Whelton PK, et al. *2017 ACC/AHA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults*. Hypertension. 2018;71:e13–e115.
8. World Health Organization — *Pulse Oximetry Training Manual* (SpO2 < 90 % hipoxemia; < 94 % vigilancia). https://www.who.int/
9. CDC — definición de fiebre (≥ 38,0 °C). https://www.cdc.gov/
10. Rango adulto de frecuencia respiratoria en reposo (12–20 rpm), referencia clínica estándar.

## Proyecto original
11. ASTRA VITAL (versión presentada a NASA Space Apps 2026): https://github.com/Etner249/astra-vital · https://etner249.github.io/astra-vital/
12. Video demo: https://youtu.be/lxITVao2RmQ · Presentación: https://youtu.be/sz9qzXasEKc

## Herramientas
Flask (https://flask.palletsprojects.com/), SQLAlchemy (https://www.sqlalchemy.org/), Flask-Login, Flask-WTF, SQLite (https://sqlite.org/), pytest (https://pytest.org/), Gunicorn, Render (https://render.com/docs).
