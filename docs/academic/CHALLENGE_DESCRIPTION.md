# Desafío NASA Space Apps Challenge 2026

**Reto:** *Create Health Monitoring Software for Astronauts on Space Missions* (dificultad intermedia; temas: exploración humana, software, exploración espacial).
Página: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/

## Resumen del reto
Las misiones de larga duración exponen a los astronautas a radiación espacial, aislamiento y confinamiento, gravedad alterada y un ambiente cerrado hostil, lo que puede provocar cambios inmunes, pérdida ósea, eventos cardiovasculares y problemas de salud conductual. Lejos de la Tierra, los astronautas asumen gran parte de la responsabilidad de detectar estos cambios. El reto pide un software visual de monitoreo que recoja indicadores de salud y permita al astronauta evaluar y actuar sobre su estado, con explicaciones sencillas, códigos de color, gráficos de evolución y, opcionalmente, gamificación y figuras interactivas del cuerpo.

## Los cinco peligros del Programa de Investigación Humana (HRP) de la NASA
1. **Radiación espacial** — rayos cósmicos y eventos de partículas solares.
2. **Aislamiento y confinamiento** — efectos conductuales, sueño, rendimiento del equipo.
3. **Distancia de la Tierra** — comunicación diferida, autonomía médica.
4. **Campos de gravedad** — pérdida ósea (~1–1,5 % por mes según NASA HRP), atrofia muscular, intolerancia ortostática.
5. **Ambientes cerrados/hostiles** — calidad del aire, CO2, microbios, inmunidad.

## Participación del equipo
- Equipo **NYXARA NOVA**, evento local Trujillo (Perú).
- Proyecto presentado: **ASTRA VITAL — Intelligent Astronaut Health Monitoring System**; enviado a evaluación el **15/11/2026 a las 16:35** (hora local), con confirmación del portal "Project Submitted for Judging".
- Recursos públicos del envío: app https://etner249.github.io/astra-vital/, código https://github.com/Etner249/astra-vital, demo https://youtu.be/lxITVao2RmQ, presentación https://youtu.be/sz9qzXasEKc.

## Problema identificado
Durante una misión larga el astronauta necesita registrar signos vitales, entender si un valor es preocupante (respecto a referencias documentadas y a su propia línea base) y saber qué hacer y cuándo avisar al médico de vuelo, aun con comunicación limitada.

## Solución propuesta (edición académica)
Una aplicación web multiusuario con Flask y SQLite donde el personal (administrador, doctor, operador) registra astronautas y mediciones; un motor de reglas explicable genera alertas persistidas con su justificación y acción sugerida; y los módulos de riesgos (5 peligros) y datos NASA dan contexto científico.
