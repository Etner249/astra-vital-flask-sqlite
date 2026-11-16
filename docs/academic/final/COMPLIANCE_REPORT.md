# ASTRA VITAL — Cumplimiento de requisitos del trabajo final

Documentos: [ASTRA_VITAL_TRABAJO_FINAL.docx](ASTRA_VITAL_TRABAJO_FINAL.docx) · [ASTRA_VITAL_TRABAJO_FINAL.pdf](ASTRA_VITAL_TRABAJO_FINAL.pdf) (68 páginas, 52 figuras, 16 tablas, índice automático)

| # | Requisito | Estado | Evidencia |
|---|---|---|---|
| 1 | Desafío NASA, problema y solución | ✅ Cumplido | Secciones 2–6; captura 21b |
| 2 | Aplicación web Flask con módulos | ✅ Cumplido | Secciones 7, 12; 15 módulos con capturas |
| 3 | SQLite con CRUD | ✅ Cumplido | Secciones 9, 11; ER desde BD real; capturas 18a–18e |
| 4 | Registro, login, logout y roles | ✅ Cumplido | Sección 10; 51 pruebas de autorización; capturas 19a–19e |
| 5 | Pruebas automatizadas | ✅ Cumplido | 136 pytest + 10 motor JS + 84 E2E; `TEST_REPORT.md` |
| 6 | GitHub y Render | ✅ Cumplido (Render Free sin persistencia, documentado) | Sección 16; capturas 20a–20h |
| 7 | Certificado NASA Space Apps | ⚠️ Pendiente | Participación verificada (21a); certificado no disponible |

## Enlaces

- App: https://etner249.github.io/astra-vital/
- API: https://astra-vital-academic.onrender.com/api/v1/health
- GitHub: https://github.com/Etner249/astra-vital · https://github.com/Etner249/astra-vital-flask-sqlite
- Entrega NASA (intacta): https://etner249.github.io/astra-vital/nasa-2026/
- Equipo: https://www.spaceappschallenge.org/2026/find-a-team/nyxara-nova/

## Datos faltantes (marcados en amarillo en la portada)

1. ~~Curso~~ ✔ Programación y Desarrollo Web
2. ~~Docente~~ ✔ Mg. Charlen Máximo Calero Huamán
3. Ciclo y sección: omitido en la portada
4. Confirmar facultad (se usó "Facultad de Ingeniería de Sistemas e Inteligencia Artificial")
5. Certificado NASA: se entrega del 1 al 6 de diciembre de 2026

Al recibirlos: editar `docs/academic/cover.json` y ejecutar `node build/build_docx.js && python3 build/finalize.py`.
