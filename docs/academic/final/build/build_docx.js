// Builds ASTRA_VITAL_TRABAJO_FINAL.docx (docx-js). Content is based on the real code, tests and evidence.
// Usage: node build_docx.js  (run from docs/academic/final/build)
const fs = require('fs');
const path = require('path');
const D = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, ShadingType,
  ImageRun, PageBreak, TableOfContents, Header, Footer, PageNumber, LevelFormat, BorderStyle, ExternalHyperlink, TabStopType } = D;

const IMG = path.join(__dirname, 'img');
const SIZES = JSON.parse(fs.readFileSync(path.join(IMG, 'sizes.json')));
const COVER = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'cover.json')));
const TESTS = JSON.parse(fs.readFileSync(path.join(__dirname, 'tests.json')));
const E2E = JSON.parse(fs.readFileSync(path.join(__dirname, 'e2e.json')));
const SCHEMA = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
const RUN_DATE = fs.readFileSync(path.join(__dirname, '..', 'tests', 'run_date.txt'), 'utf8').trim();
const FONT = 'Calibri', MONO = 'Consolas', NAVY = '0B2545', BLUE = '1E6FD9', GREY = '5B6B82';
const CW = 9026; // A4 content width in DXA with 1" margins (11906 - 2*1440)

let figN = 0, tabN = 0;
// ---------- inline markup: **bold**, *italic*, `code`, [text](url)
function runs(text, base = {}) {
  const out = []; const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g; let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith('`')) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: (base.size || 22) - 2, color: '1F3A60' }));
    else if (t.startsWith('[')) { const mm = t.match(/\[([^\]]+)\]\(([^)]+)\)/); out.push(new ExternalHyperlink({ link: mm[2], children: [new TextRun({ text: mm[1], style: 'Hyperlink', ...base })] })); }
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t, o.run || {}), alignment: o.align || AlignmentType.JUSTIFIED, spacing: { after: 120, line: 300 }, ...o.p });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (items, ref = 'bul') => items.map(t => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 280 }, alignment: AlignmentType.LEFT }));
const N = (items, inst) => items.map(t => new Paragraph({ numbering: { reference: 'num', level: 0, instance: inst }, children: runs(t), spacing: { after: 60, line: 280 } }));
let numInst = 1;
const NL = items => N(items, numInst++);
const NOTE = t => new Paragraph({ children: runs(t, { size: 20, color: '5A4200' }), shading: { type: ShadingType.CLEAR, fill: 'FFF6DD' }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: 'E0A800', space: 6 } }, spacing: { before: 80, after: 160, line: 276 }, indent: { left: 120, right: 120 } });
const CODE = text => text.split('\n').map(l => new Paragraph({ children: [new TextRun({ text: l || ' ', font: MONO, size: 15 })], spacing: { after: 0, line: 220 }, shading: { type: ShadingType.CLEAR, fill: 'F3F5F8' } }));

function fig(file, caption, maxW = 600, maxH = 760) {
  const [w, h] = SIZES[file]; let W = maxW, H = Math.round(h * maxW / w);
  if (H > maxH) { H = maxH; W = Math.round(w * maxH / h); }
  figN++;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [new ImageRun({ type: file.endsWith('.png') ? 'png' : 'jpg', data: fs.readFileSync(path.join(IMG, file)), transformation: { width: W, height: H }, altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: `Figura ${figN}. `, bold: true, size: 19, color: NAVY }), ...runs(caption, { size: 19, color: GREY }), new TextRun({ text: `  [${file.replace(/\.(jpg|png)$/, '')}]`, size: 15, color: '8A97AB' })] })
  ];
}
function table(headers, rows, widths, opt = {}) {
  tabN++;
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({ width: { size: widths[i], type: WidthType.DXA }, shading: head ? { type: ShadingType.CLEAR, fill: '1E3A5F' } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ spacing: { after: 0, line: 252 }, children: runs(String(t), head ? { bold: true, color: 'FFFFFF', size: 18 } : { size: 18 }) })] });
  const t = new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] });
  return [new Paragraph({ keepNext: true, spacing: { before: 160, after: 60 }, children: [new TextRun({ text: `Tabla ${tabN}. `, bold: true, size: 19, color: NAVY }), ...runs(opt.caption || '', { size: 19, color: GREY })] }), t, new Paragraph({ spacing: { after: 120 }, children: [] })];
}
const pend = (v, label) => v ? [new TextRun({ text: v, size: 24 })] : [new TextRun({ text: `[PENDIENTE — ${label}]`, size: 24, color: 'B42318', bold: true, highlight: 'yellow' })];

// ======================================================= COVER
const coverRow = (k, v) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: k + ': ', bold: true, size: 24, color: NAVY }), ...v] });
const cover = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400, after: 60 }, children: [new TextRun({ text: 'UNIVERSIDAD PRIVADA DE TRUJILLO', bold: true, size: 34, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: COVER.faculty ? [new TextRun({ text: COVER.faculty.toUpperCase(), size: 24, color: GREY })] : pend(null, 'Facultad') }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(__dirname, 'logo_cover.png')), transformation: { width: 380, height: 73 }, altText: { title: 'ASTRA VITAL', description: 'Logotipo ASTRA VITAL', name: 'logo' } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: 'TRABAJO FINAL DEL CURSO', bold: true, size: 28, color: BLUE })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [new TextRun({ text: 'Desarrollo de una aplicación web con Python Flask y SQLite', size: 26, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: 'ASTRA VITAL', bold: true, size: 52, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 500 }, children: [new TextRun({ text: 'Sistema web de monitoreo de salud de astronautas — NASA Space Apps Challenge 2026', size: 24, color: GREY })] }),
  coverRow('Curso', pend(COVER.course, 'nombre exacto del curso')),
  coverRow('Docente', pend(COVER.professor, 'docente')),
  coverRow('Ciclo / sección', pend(COVER.cycle_section, 'ciclo y sección')),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300, after: 80 }, children: [new TextRun({ text: 'Integrantes — equipo NYXARA NOVA', bold: true, size: 24, color: NAVY })] }),
  ...COVER.members.map(m => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [new TextRun({ text: m, size: 24 })] })),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600 }, children: [new TextRun({ text: COVER.city_date, size: 22, color: GREY })] }),
];

// ======================================================= BODY
const roleRows = [
  ['Ver dashboard, astronautas, misiones, mediciones, alertas, riesgos, datos NASA', 'Sí', 'Sí', 'Sí'],
  ['Registrar mediciones (`measurements.create`)', 'Sí', 'Sí', 'Sí'],
  ['Editar mediciones (`measurements.edit`)', 'Sí', 'Sí', 'No'],
  ['Eliminar mediciones (`measurements.delete`)', 'Sí', 'No', 'No'],
  ['Revisar alertas (`alerts.manage`)', 'Sí', 'Sí', 'No'],
  ['Gestionar astronautas (`astronauts.manage`)', 'Sí', 'No', 'No'],
  ['Gestionar misiones (`missions.manage`)', 'Sí', 'No', 'No'],
  ['Reportes (`reports.view`)', 'Sí', 'Sí', 'No'],
  ['Gestionar usuarios (`users.manage`)', 'Sí*', 'No', 'No'],
  ['Auditoría (`audit.view`)', 'Sí', 'No', 'No'],
];
const endpoints = [
  ['GET', '/api/v1/health', 'Público', 'Estado del servicio (usado para detectar el "despertar" de Render)'],
  ['GET', '/api/v1/demo-accounts', 'Público', 'Cuentas públicas de demostración (si DEMO_ACCOUNTS=1)'],
  ['POST', '/api/v1/auth/login', 'Público', 'Devuelve token Bearer (8 h) y permisos del usuario'],
  ['GET', '/api/v1/auth/me', 'Token', 'Usuario actual, rol y permisos'],
  ['POST', '/api/v1/auth/logout', 'Token', 'Revoca el token'],
  ['GET / POST', '/api/v1/missions', 'missions.view / manage', 'Listar / crear misiones'],
  ['PUT / DELETE', '/api/v1/missions/{id}', 'missions.manage', 'Editar / eliminar (409 si tiene astronautas)'],
  ['GET / POST', '/api/v1/astronauts', 'astronauts.view / manage', 'Listar / crear astronautas'],
  ['GET / PUT / DELETE', '/api/v1/astronauts/{id}', 'view / manage', 'Detalle, edición, eliminación en cascada'],
  ['GET / POST', '/api/v1/measurements', 'measurements.view / create', 'Filtros astronaut_id, from, to, limit, offset; creación genera alertas'],
  ['PUT', '/api/v1/measurements/{id}', 'measurements.edit', 'Edición y recálculo de alertas'],
  ['DELETE', '/api/v1/measurements/{id}', 'measurements.delete', 'Eliminación (conserva alertas revisadas)'],
  ['GET', '/api/v1/alerts', 'alerts.view', 'Filtros por astronauta, estado y nivel'],
  ['PATCH', '/api/v1/alerts/{id}', 'alerts.manage', 'Revisión: estado y notas'],
  ['GET / POST', '/api/v1/users', 'users.manage', 'Listar / crear usuarios (solo lectura para la cuenta demo)'],
  ['PUT / DELETE', '/api/v1/users/{id}', 'users.manage', 'Editar / eliminar (no el propio ni el último admin)'],
  ['GET', '/api/v1/audit', 'audit.view', 'Últimas 200 acciones (IP oculta para cuentas demo)'],
  ['GET', '/api/v1/reports/summary', 'reports.view', 'Totales y estado por astronauta'],
];
const perFile = {}; TESTS.forEach(([f]) => perFile[f] = (perFile[f] || 0) + 1);
const testDesc = {
  'tests/test_api.py': 'API v1: CORS permitido/rechazado, preflight, login Bearer, hash del token, expiración, revocación, cuenta inactiva, límite de intentos, matriz de permisos, CRUD de misiones/astronautas/mediciones, revisión de alertas, cuentas demo, errores JSON.',
  'tests/test_auth.py': 'Registro válido/inválido/duplicado, login correcto e incorrecto, cuenta inactiva, logout, redirección de rutas protegidas, bloqueo de open redirect, cambio de contraseña.',
  'tests/test_authorization.py': 'Acceso permitido por rol a cada ruta HTML y 403 por rol; operador sin edición/eliminación ni revisión.',
  'tests/test_crud.py': 'CRUD de astronautas, mediciones, misiones y usuarios en la interfaz Flask; cascadas; alertas persistidas; exportación CSV.',
  'tests/test_demo_accounts.py': 'Seed idempotente de cuentas demo, login por rol, credenciales sin secretos, límites de seguridad de las cuentas públicas.',
  'tests/test_engine.py': 'Motor de reglas: SpO2, presión, consolidación, estado global y reglas de los 9 indicadores originales.',
  'tests/test_security.py': 'Hash de contraseñas, CSRF, validación de entradas, CHECK y FK en SQLite, cabeceras de seguridad, escape XSS.'
};

const body = [];
const add = (...xs) => xs.forEach(x => Array.isArray(x) ? body.push(...x) : body.push(x));

add(H1('1. Introducción'),
  P('Las misiones espaciales de larga duración —estancias de seis meses en la Estación Espacial Internacional y, en el futuro, viajes a la Luna y a Marte— exponen a la tripulación a radiación, aislamiento, gravedad alterada y ambientes cerrados. A medida que aumenta la distancia, la comunicación con el equipo médico en Tierra se retrasa o se interrumpe, y el propio astronauta asume la responsabilidad de vigilar su salud y decidir cuándo pedir ayuda.'),
  P('**ASTRA VITAL** es la respuesta del equipo **NYXARA NOVA** (Trujillo, Perú) al desafío *Create Health Monitoring Software for Astronauts on Space Missions* del NASA Space Apps Challenge 2026. El proyecto se presentó oficialmente el 15 de noviembre de 2026 como una aplicación web estática con un motor de reglas en JavaScript. Para este curso, el equipo amplió el proyecto con un **backend en Python Flask y SQLite**, autenticación, roles, operaciones CRUD, una API REST, pruebas automatizadas y despliegue en la nube.'),
  P('Este documento describe el sistema realmente implementado: su arquitectura, base de datos, gestión de usuarios, módulos, motor de alertas, pruebas y despliegue, junto con las evidencias obtenidas de la aplicación en ejecución. La versión entregada a la NASA se conserva sin cambios en [https://etner249.github.io/astra-vital/nasa-2026/](https://etner249.github.io/astra-vital/nasa-2026/); todas las funciones de backend descritas aquí son **posteriores** a esa entrega.'),
  NOTE('ASTRA VITAL es un prototipo educativo y de investigación: no es un dispositivo médico, no diagnostica y no reemplaza a los médicos de vuelo. Los astronautas y signos vitales de demostración son sintéticos.'));

add(H1('2. Descripción del desafío NASA'),
  H2('2.1 Desafío seleccionado'),
  P('**Desafío:** *Create Health Monitoring Software for Astronauts on Space Missions* (NASA Space Apps Challenge 2026). Según el enunciado publicado en la página del proyecto del equipo, las misiones de larga duración exponen a los astronautas a radiación espacial, aislamiento y confinamiento, gravedad alterada y un ambiente cerrado hostil, lo que puede provocar cambios inmunes, pérdida ósea, eventos cardiovasculares y problemas de salud conductual; en misiones largas los astronautas cargan con gran parte de la responsabilidad de detectar estos cambios. El reto pide un software que reúna indicadores de salud y permita al astronauta evaluar su estado y actuar.'),
  ...fig('21b_space_apps_project_challenge.jpg', 'Enunciado del desafío en la página del proyecto NYXARA NOVA (spaceappschallenge.org).', 520),
  H2('2.2 Los cinco peligros del vuelo espacial humano'),
  P('El Programa de Investigación Humana (HRP) de la NASA agrupa los riesgos del vuelo espacial en cinco peligros. ASTRA VITAL relaciona cada indicador con ellos en el módulo *Mission Risk Center*.'),
  ...table(['Peligro (NASA HRP)', 'Efectos relevantes', 'Indicadores relacionados en ASTRA VITAL'], [
    ['Radiación espacial', 'Riesgo de cáncer, efectos en sistema nervioso y tejidos', 'No se mide dosis; indirectos: temperatura, fatiga, laboratorio'],
    ['Aislamiento y confinamiento', 'Ánimo, sueño, desempeño del equipo', 'Sueño, fatiga (Samn-Perelli), ánimo'],
    ['Distancia de la Tierra', 'Soporte médico diferido, autonomía', 'Todos; tiempo desde el último contacto; cola de sincronización'],
    ['Campos de gravedad', 'Pérdida ósea (~1–1,5 %/mes), músculo, intolerancia ortostática', 'Ejercicio, frecuencia cardiaca, presión arterial'],
    ['Ambientes cerrados/hostiles', 'Inmunidad, CO2, microbios', 'SpO2, temperatura, sueño, fatiga'],
  ], [2300, 3300, 3426], { caption: 'Peligros del HRP y su relación con los indicadores del sistema.' }));

add(H1('3. Planteamiento del problema'),
  P('Durante una misión larga, la tripulación y el personal de apoyo necesitan registrar signos vitales de forma ordenada y trazable, interpretar si un valor es preocupante —frente a referencias clínicas y frente a la propia línea base del astronauta—, saber qué hacer y cuándo contactar al médico de vuelo, conservar el historial con revisión médica y, al mismo tiempo, controlar quién puede modificar datos clínicos.'),
  P('La versión enviada a la NASA resolvía la interpretación dentro del navegador, con datos locales y una sincronización con Tierra **simulada**. No tenía usuarios, roles, base de datos compartida ni pruebas de backend. El problema académico consiste en convertir ese prototipo en una aplicación web con Flask y SQLite que cumpla los requisitos del curso sin perder sus diez módulos ni sus nueve indicadores.'));

add(H1('4. Justificación'),
  ...B(['**Relevancia científica:** la NASA identifica la detección temprana de cambios de salud como una necesidad de las misiones de exploración; el desafío lo plantea explícitamente.',
    '**Valor técnico-académico:** el proyecto integra en un caso real todos los contenidos del curso: aplicación Flask modular, ORM sobre SQLite, CRUD, autenticación, autorización por roles, API REST, pruebas automatizadas y despliegue.',
    '**Transparencia:** el motor usa reglas explicables (sin modelos de caja negra) y cada alerta indica su regla y fuente, lo que permite auditar el comportamiento del sistema.',
    '**Uso de datos abiertos de la NASA:** se incorporan datos reales de laboratorio del repositorio NASA OSDR (misión Inspiration4).',
    '**Evaluabilidad:** tres cuentas públicas de demostración permiten a docentes y jurados probar cada rol sin credenciales privadas.']));

add(H1('5. Objetivos'),
  H2('5.1 Objetivo general'),
  P('Desarrollar y desplegar una aplicación web con Python Flask y SQLite que permita registrar astronautas, misiones y nueve indicadores de salud, generar y revisar alertas explicables, y controlar el acceso por roles, integrando el frontend original de ASTRA VITAL publicado en GitHub Pages.'),
  H2('5.2 Objetivos específicos'),
  ...NL(['Diseñar una base de datos SQLite normalizada con claves primarias y foráneas, restricciones CHECK/UNIQUE e índices.',
    'Implementar operaciones CRUD de usuarios, astronautas, misiones, mediciones y alertas, tanto en la interfaz Flask como en una API REST.',
    'Implementar registro, inicio y cierre de sesión, sesiones y tokens, y control de acceso por roles verificado en el backend.',
    'Portar a Python el motor de reglas de ASTRA VITAL y persistir sus alertas.',
    'Conectar el frontend de GitHub Pages con el backend en Render mediante HTTPS, tokens Bearer y CORS restringido.',
    'Verificar el sistema con pruebas automatizadas (pytest, pruebas del motor JavaScript y pruebas de interfaz con Playwright).',
    'Publicar el código en GitHub y desplegar la aplicación en Render, documentando sus limitaciones.']));

add(H1('6. Descripción de la solución'),
  H2('6.1 Visión general'),
  P('ASTRA VITAL Academic Edition está formado por dos piezas que trabajan juntas:'),
  ...B(['**Frontend** (repositorio `astra-vital`, publicado en GitHub Pages): la aplicación original de una sola página, con los diez módulos de la entrega NASA, ampliada con el login *NASA Evaluator Access*, un *Project Briefing* en inglés y cinco módulos académicos de gestión.',
    '**Backend** (repositorio `astra-vital-flask-sqlite`, desplegado en Render): aplicación Flask con base SQLite, API REST `/api/v1`, interfaz HTML propia (Jinja2), motor de reglas en Python, auditoría y comandos de inicialización.']),
  P('Al iniciar sesión, el frontend obtiene un token, carga los astronautas y sus mediciones desde la API y las convierte al formato de registro de la aplicación original, de modo que los módulos originales funcionan igual pero con datos compartidos en SQLite. Cada medición nueva se guarda primero en el navegador y se envía al servidor cuando el enlace simulado con Tierra está abierto (AOS).'),
  ...fig('01_login.jpg', 'Pantalla de acceso de la aplicación (NASA Evaluator Access y Project Briefing).'),
  H2('6.2 Qué es real y qué es simulado'),
  ...table(['Real', 'Simulado'], [
    ['Datos de laboratorio NASA OSDR OSD-575 y OSD-569', 'Astronautas de demostración (ficticios)'],
    ['Mediciones ingresadas por los usuarios', 'Signos vitales sintéticos del seed'],
    ['Autenticación, tokens, roles y permisos', 'Escenario de misión y tendencias generadas'],
    ['Registros en SQLite mientras el servicio está activo', 'Retardo de comunicación y ventanas AOS/LOS'],
    ['Pruebas automatizadas y despliegue', 'Sincronización con Tierra de la versión original'],
  ], [4513, 4513], { caption: 'Elementos reales y simulados del sistema.' }));

add(H1('7. Arquitectura del sistema'),
  P('La arquitectura separa el frontend estático (GitHub Pages) del backend dinámico (Render). Flask no se ejecuta en GitHub Pages: la página es estática y se comunica con la API por HTTPS.'),
  ...fig('architecture.png', 'Arquitectura de despliegue de ASTRA VITAL Academic Edition.'),
  H2('7.1 Frontend'),
  P('Archivo único `index.html` generado por `build.py`, que incrusta `src/styles.css`, `src/engine.js` (motor de reglas original), `src/app.js` (interfaz, enrutamiento por `#hash`, cliente de API, cola offline) y el subconjunto de datos OSDR. `build.py` inyecta la URL de la API y una política CSP que solo permite conexiones a ese origen. La copia de la entrega NASA está en `nasa-2026/index.html` y nunca se reconstruye.'),
  H2('7.2 Backend Flask'),
  ...table(['Componente', 'Archivo', 'Responsabilidad'], [
    ['App factory', '`app/__init__.py`', 'Configuración, extensiones, cabeceras de seguridad, manejadores de error, comandos CLI (`init-db`, `create-user`, `seed-demo`, `seed-demo-accounts`, `bootstrap`)'],
    ['Configuración', '`app/config.py`', 'SECRET_KEY, DATABASE_PATH, CORS_ORIGINS, API_TOKEN_HOURS, DEMO_ACCOUNTS; perfiles desarrollo, producción y pruebas'],
    ['Modelos', '`app/models.py`', '7 modelos SQLAlchemy con restricciones'],
    ['API REST', '`app/api.py`', 'Blueprint `/api/v1`: autenticación Bearer, CORS, CRUD, alertas, usuarios, auditoría'],
    ['Interfaz HTML', '`app/auth.py`, `app/main.py`, `app/crud.py`', 'Blueprints con plantillas Jinja2 y formularios WTForms'],
    ['Permisos', '`app/decorators.py`, `app/demo.py`', 'Matriz de permisos, `permission_required`, límites de cuentas demo'],
    ['Motor y servicios', '`app/engine.py`, `app/services.py`', 'Reglas de alertas; generación, persistencia y auditoría'],
    ['Datos de demostración', '`app/seed.py`', 'Misiones, astronautas y 21 días de mediciones sintéticas'],
  ], [1700, 2600, 4726], { caption: 'Organización modular del backend.' }),
  H2('7.3 Funcionamiento de la API y comunicación GitHub Pages ↔ Render'),
  P('El frontend y el backend están en dominios distintos (`etner249.github.io` y `astra-vital-academic.onrender.com`). Por eso la API usa **tokens Bearer** en lugar de cookies: los navegadores bloquean cada vez más las cookies de terceros, y sin cookies el ataque CSRF no aplica. El backend solo devuelve cabeceras CORS al origen exacto configurado en `CORS_ORIGINS` y rechaza con 403 cualquier otro origen.'),
  ...fig('auth_flow.png', 'Flujo de autenticación y autorización entre GitHub Pages y la API Flask.', 470, 600),
  ...table(['Método', 'Ruta', 'Permiso', 'Descripción'], endpoints, [1300, 2700, 1900, 3126], { caption: 'Endpoints reales de la API v1 (`app/api.py`).' }),
  H2('7.4 Funcionamiento offline-first'),
  P('Cada medición se valida (`checkQuality`) y se guarda en `localStorage` en una cola propia de cada usuario y astronauta. Si el enlace simulado está en LOS, los registros quedan en cola; en AOS se envían en lotes de cinco a `POST /api/v1/measurements` y solo salen de la cola cuando el servidor confirma. Los valores rechazados por la validación del servidor (HTTP 422) se registran en el log de sincronización.'),
  ...fig('sync_flow.png', 'Flujo de registro y sincronización (AOS/LOS simulado).', 330, 430));

add(H1('8. Tecnologías utilizadas'),
  ...table(['Capa', 'Tecnología', 'Uso en el proyecto'], [
    ['Lenguaje backend', 'Python 3', 'API, interfaz Flask, motor de reglas, pruebas'],
    ['Framework web', 'Flask 3.1.3', 'App factory, blueprints, plantillas Jinja2'],
    ['ORM / BD', 'Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.8, SQLite 3', 'Modelos, consultas, restricciones, claves foráneas'],
    ['Autenticación', 'Flask-Login 0.6.3, Werkzeug (scrypt)', 'Sesiones de la interfaz HTML y hash de contraseñas'],
    ['Formularios', 'Flask-WTF 1.3.0, WTForms 3.3.2, email-validator', 'Validación y protección CSRF; reutilizados por la API'],
    ['Servidor', 'Gunicorn 27.0.1 (2 workers, 2 hilos)', 'Servidor WSGI en Render'],
    ['Frontend', 'HTML5, CSS3, JavaScript (sin frameworks), SVG', 'Interfaz, gráficos, cliente de API'],
    ['Pruebas', 'pytest 9.1.1, Node.js, Playwright + Chrome', 'Pruebas unitarias, de API, de seguridad y E2E'],
    ['Hosting', 'GitHub Pages, Render (plan Free)', 'Frontend estático y backend Flask'],
    ['Control de versiones', 'Git, GitHub', 'Repositorios públicos frontend y backend'],
  ], [1900, 3200, 3926], { caption: 'Tecnologías verificadas en `requirements.txt` y en el código.' }));

add(H1('9. Diseño de base de datos'),
  P('La base SQLite se crea de forma reproducible con `flask bootstrap` (`db.create_all()`). En cada conexión se activa `PRAGMA foreign_keys=ON` y el modo WAL. El diagrama se generó a partir del esquema real de la base (`sqlite_master` y `PRAGMA foreign_key_list`).'),
  ...fig('er_diagram.png', 'Diagrama entidad-relación generado desde la base SQLite real (7 tablas).'),
  ...table(['Tabla', 'Propósito', 'Claves y relaciones'], [
    ['users', 'Usuarios y roles; `is_demo` marca las 3 cuentas públicas', 'PK id; email UNIQUE; CHECK role IN (admin, doctor, operator)'],
    ['missions', 'Misiones (ficticias en la demo)', 'PK id; code UNIQUE; CHECK duración 1–1500 y estado'],
    ['astronauts', 'Tripulantes', 'PK id; code UNIQUE; FK mission_id → missions (RESTRICT); CHECK edad 18–80 y estado'],
    ['health_measurements', 'Mediciones: 6 signos vitales + 5 indicadores originales', 'PK id; FK astronaut_id (CASCADE); FK recorded_by_id → users (SET NULL); índice (astronaut_id, measured_at)'],
    ['health_alerts', 'Alertas explicables y su revisión', 'PK id; FK astronaut_id (CASCADE); FK measurement_id (SET NULL); FK reviewed_by_id (SET NULL); índice (status, level)'],
    ['audit_logs', 'Auditoría de accesos y cambios', 'PK id; FK user_id (SET NULL); índice created_at'],
    ['api_tokens', 'Tokens de la API (solo hash SHA-256)', 'PK id; token_hash UNIQUE; FK user_id (CASCADE)'],
  ], [1900, 3300, 3826], { caption: 'Tablas del esquema real.' }),
  ...table(['Campo', 'Rango permitido (CHECK)', 'Campo', 'Rango permitido (CHECK)'], [
    ['heart_rate', '25–230 lpm', 'sleep_hours', '0–16 h'],
    ['systolic_bp', '60–260 mmHg', 'exercise_min', '0–400 min'],
    ['diastolic_bp', '30–160 mmHg', 'fatigue', '1–7 (Samn-Perelli)'],
    ['spo2', '50–100 %', 'mood', '1–5'],
    ['temperature', '32–43 °C', 'glucose', '20–600 mg/dL'],
    ['respiratory_rate', '4–60 rpm', '', ''],
  ], [2000, 2513, 2000, 2513], { caption: 'Restricciones CHECK de `health_measurements` (además de las validaciones WTForms).' }),
  P('Las validaciones se aplican en dos niveles: WTForms (mensajes al usuario, p. ej. diastólica menor que sistólica y al menos un indicador) y restricciones de SQLite (última barrera). Las pruebas `test_database_check_constraint` y `test_foreign_keys_enforced` comprueban que la base rechaza datos inválidos. El DDL completo está en el Anexo A.'));

add(H1('10. Gestión de usuarios y permisos'),
  H2('10.1 Registro e inicialización de usuarios'),
  ...B(['**Interfaz Flask** (`/register`): registro público que crea siempre cuentas con rol **Operador** (mínimo privilegio); contraseña de al menos 10 caracteres con letras y números.',
    '**API** (`POST /api/v1/users`): un Administrador crea usuarios y asigna roles.',
    '**CLI:** `flask create-user` (pide la contraseña por consola) y `flask bootstrap`, que crea los usuarios privados a partir de variables de entorno que Render genera (`generateValue`), sin exponerlas en el repositorio.',
    '**Cuentas públicas de demostración:** `flask seed-demo-accounts` / `bootstrap` ejecutan `ensure_demo_accounts()`, idempotente: no duplica filas y restaura rol, estado y contraseña si alguien las altera.']),
  H2('10.2 Inicio de sesión, sesiones y tokens'),
  P('En la interfaz HTML se usan sesiones de Flask-Login con cookies HttpOnly, SameSite=Lax y Secure en producción. En la API, `POST /auth/login` verifica el hash scrypt y devuelve un token aleatorio de 256 bits; en la base solo se guarda su SHA-256, con expiración de 8 horas. El frontend lo guarda en `sessionStorage` y lo envía en la cabecera `Authorization`. Los mensajes de error son genéricos ("Incorrect email or password") y los intentos fallidos se registran en la auditoría.'),
  ...fig('02c_login_error.jpg', 'Login con credenciales incorrectas: mensaje genérico en inglés.', 380),
  H2('10.3 Cierre de sesión'),
  P('`POST /api/v1/auth/logout` marca el token como revocado (`revoked_at`). En la interfaz HTML el logout es un POST protegido con CSRF. Si el servidor se reinicia, el token deja de existir y el frontend vuelve al login con un aviso.'),
  ...fig('02d_after_logout.jpg', 'Pantalla de acceso después de cerrar sesión.', 380),
  H2('10.4 Roles y permisos'),
  ...table(['Capacidad (permiso)', 'Administrador', 'Médico / Especialista', 'Operador'], roleRows, [4826, 1400, 1500, 1300], { caption: 'Matriz de permisos aplicada en el backend (`app/decorators.py`). *Solo lectura para la cuenta demo de administrador.' }),
  H2('10.5 Protección de rutas y restricciones del backend'),
  ...B(['Cada ruta de la API llama a `_require(permiso)`; cada ruta HTML usa `@permission_required`. Si el rol no tiene el permiso, responde **403**, aunque el usuario escriba la URL directamente.',
    'La API solo acepta tokens Bearer: una cookie de sesión no autentica peticiones a `/api/v1` (verificado por `test_cookie_session_is_not_accepted_by_api`).',
    'Límites de las cuentas públicas (`app/demo.py`): gestión de usuarios de solo lectura, sin cambio de contraseña, sin borrado de los datos sintéticos de referencia, y correos privados e IP de auditoría enmascarados.',
    'Un administrador no puede eliminarse a sí mismo, quitarse el rol ni eliminar al último administrador.']),
  ...fig('02_demo_accounts.jpg', 'Cuentas públicas de demostración con instrucciones de acceso.', 400),
  ...fig('19c_operator_navigation.jpg', 'Navegación del Operador: no aparecen Users ni Audit.'),
  ...fig('19b_doctor_users_blocked_redirect.jpg', 'El Médico escribe `#users` y la aplicación lo devuelve al dashboard (el backend respondería 403).'),
  ...fig('16_users_admin_demo_read_only.jpg', 'Gestión de usuarios en solo lectura para la cuenta demo de administrador.'),
  ...fig('14c_demo_limit_synthetic_delete_blocked.jpg', 'Restricción del backend: la cuenta demo no puede borrar datos sintéticos de referencia.'));

add(H1('11. Operaciones CRUD'),
  ...table(['Entidad', 'CREATE', 'READ', 'UPDATE', 'DELETE'], [
    ['Usuarios', 'Admin; registro público (operador)', 'Admin', 'Admin; contraseña propia', 'Admin (con protecciones)'],
    ['Astronautas', 'Admin', 'Todos (lista, búsqueda, detalle)', 'Admin', 'Admin; cascada a mediciones y alertas; confirmación con alertas prioritarias'],
    ['Misiones', 'Admin', 'Todos', 'Admin', 'Admin; 409 si tiene astronautas'],
    ['Mediciones', 'Todos los roles', 'Todos; filtros por astronauta y fechas', 'Admin y Médico; recalcula alertas', 'Solo Admin'],
    ['Alertas', 'Automática (motor)', 'Todos; filtros por estado y nivel', 'Admin y Médico (revisión)', 'Al eliminar el astronauta o la medición (abiertas)'],
  ], [1400, 1900, 1900, 1900, 1926], { caption: 'Operaciones CRUD por entidad.' }),
  P('Cada escritura pasa por validación WTForms, restricciones SQLite y un registro en `audit_logs`. La secuencia siguiente, capturada en la aplicación en ejecución, muestra el ciclo completo sobre un astronauta.'),
  ...fig('18a_crud_create_astronaut_form.jpg', 'CREATE: formulario de nuevo astronauta.'),
  ...fig('18b_crud_read_astronaut_created.jpg', 'READ: el astronauta creado aparece en la lista.'),
  ...fig('18c_crud_update_astronaut.jpg', 'UPDATE: rol y estado actualizados.'),
  ...fig('18d_crud_delete_confirmation.jpg', 'DELETE: confirmación en dos pasos.', 600),
  ...fig('18e_crud_deleted.jpg', 'DELETE: registro eliminado (mensaje de confirmación).'),
  ...fig('14b_measurement_edit_form.jpg', 'UPDATE de una medición (Administrador o Médico).', 560));

const modules = [
  ['Mission Dashboard', 'Estado global, indicadores con mini-gráficos, alertas activas, día de misión, contacto con Tierra, cola y rutina diaria.', '03_dashboard_admin.jpg'],
  ['Log Measurement', 'Formulario validado con unidad, fecha, fuente, notas y guía de medición para los 9 indicadores.', '04a_log_measurement_form.jpg'],
  ['Astronaut Profile', 'Perfil del tripulante y misión, líneas base personales e historial de eventos.', '05_astronaut_profile.jpg'],
  ['Interactive Body', 'Sistemas cardiovascular, musculoesquelético, nervioso/conductual, inmune y general con estado por color, ícono y texto.', '06_interactive_body.jpg'],
  ['Health Intelligence', 'Alertas explicables: qué cambió, indicador, por qué importa, acción sugerida, contacto médico, regla y fuente.', '07_health_intelligence.jpg'],
  ['Mission Risk Center', 'Los cinco peligros del HRP con riesgos, indicadores, medidas preventivas y limitaciones.', '08_mission_risk_center.jpg'],
  ['NASA Data (OSDR)', 'Datos reales de laboratorio de Inspiration4 (OSD-575, OSD-569) con rangos y controles de calidad.', '09_nasa_data.jpg'],
  ['Sync & Reports', 'Cola offline, AOS/LOS simulado, sincronización con la API, reportes, CSV y respaldo.', '11a_sync_los_queue.jpg'],
  ['Ground Console', 'Vista médica de los datos sincronizados y de las alertas guardadas en SQLite, con revisión según el rol.', '10_ground_console.jpg'],
  ['About & References', 'Referencias científicas, datos reales/sintéticos y limitaciones.', null],
];
add(H1('12. Descripción de módulos'),
  P('La aplicación conserva los **diez módulos de la entrega NASA** y añade **cinco módulos académicos** que solo aparecen según los permisos del rol. Las capturas son de la aplicación real en ejecución con datos sintéticos.'),
  H2('12.1 Módulos originales'));
modules.forEach(([n, d, img], i) => { add(H3(`12.1.${i + 1} ${n}`), P(d)); if (img) add(...fig(img, `Módulo ${n}.`)); });
add(H2('12.2 Módulos académicos (añadidos después de la entrega NASA)'),
  H3('12.2.1 Crew & Missions'), P('CRUD de astronautas y misiones con estado de salud por astronauta; selección del astronauta activo.'), ...fig('12a_crew_and_missions_list.jpg', 'Gestión de astronautas.'), ...fig('13_missions_management.jpg', 'Gestión de misiones.', 600),
  H3('12.2.2 Measurements Database'), P('Tabla de mediciones de SQLite con filtros por astronauta y fechas, paginación y botones según el rol.'), ...fig('14a_measurements_database.jpg', 'Base de datos de mediciones filtrada por astronauta.'),
  H3('12.2.3 Alert Review'), P('Alertas persistidas con filtros por estado, nivel y astronauta; el Médico y el Administrador registran estado y notas.'), ...fig('15b_alert_review_doctor_saved.jpg', 'Revisión de una alerta por el Médico.'),
  H3('12.2.4 Users & Roles'), P('Gestión de usuarios y matriz de permisos (solo lectura para la cuenta demo).'), ...fig('16_users_admin_demo_read_only.jpg', 'Usuarios y roles.'),
  H3('12.2.5 Audit Log'), P('Últimas 200 acciones con usuario, acción, entidad e IP (oculta para cuentas demo).'), ...fig('17_audit_log.jpg', 'Registro de auditoría.'));

add(H1('13. Motor de alertas'),
  P('El motor es determinista y explicable: no contiene modelos de aprendizaje automático. Existen dos implementaciones coherentes: `src/engine.js` (frontend, análisis de los módulos originales) y `app/engine.py` (backend, alertas persistidas en SQLite al guardar cada medición).'),
  ...table(['Indicador', 'Seguimiento', 'Prioritaria', 'Fuente'], [
    ['Frecuencia cardiaca', 'Fuera de 60–100 lpm', '—', 'AHA'],
    ['Presión arterial', '≥ 140/90 (estadio 2) o < 90/60', '> 180 y/o > 120', 'ACC/AHA 2017'],
    ['SpO2', '90–94 %', '< 90 %', 'OMS 2011'],
    ['Temperatura', '—', '≥ 38,0 °C', 'CDC'],
    ['Frecuencia respiratoria (backend)', 'Fuera de 12–20 rpm', '—', 'Referencia clínica'],
    ['Sueño', '3 periodos seguidos < 7 h (1 periodo: informativa)', '—', 'AASM/SRS'],
    ['Ejercicio', '3 días seguidos < 120 min', '—', 'NASA'],
    ['Fatiga (Samn-Perelli)', '≥ 5', '—', 'Samn & Perelli 1982'],
    ['Glucosa', '< 70 mg/dL', '< 54 mg/dL', 'ADA'],
    ['Cualquiera', 'Desviación ≥ 2 DE frente a las primeras 7 mediciones', '—', 'Convención del motor'],
  ], [2300, 3100, 1700, 1926], { caption: 'Reglas de referencia implementadas (`app/engine.py`, `src/engine.js`).' }),
  P('El motor del frontend aplica además cinco categorías: calidad de datos, datos faltantes (> 36 h sin medición), rangos de referencia, desviación de línea base (≥ 2 DE) y tendencias de siete días. Los hallazgos del mismo indicador se consolidan en una sola alerta que explica qué cambió, por qué importa, la acción sugerida, cuándo contactar al equipo médico y la regla y fuente que la respaldan.'),
  NOTE('Las convenciones de ingeniería (2 DE, tendencia de 7 días, ventana de 36 h) requieren validación clínica; las alertas son asociaciones, no diagnósticos.'),
  ...fig('04b_log_measurement_saved.jpg', 'Medición de presión 142/88 guardada: el servidor confirma y genera la alerta correspondiente.'));

add(H1('14. Datos NASA OSDR'),
  P('El módulo NASA Data usa un subconjunto real (`data/osdr_i4_subset.json`) de dos estudios del NASA Open Science Data Repository sobre la misión SpaceX Inspiration4:'),
  ...B(['[OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575): *Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays*.',
    '[OSD-569](https://osdr.nasa.gov/bio/repo/data/studies/OSD-569): mediciones de sangre completa (incluye hemograma, CBC).']),
  P('Son análisis de laboratorio de cuatro tripulantes civiles, tomados antes (L-92, L-44, L-3) y después (R+1, R+45, R+82, R+194) de una misión de tres días. **No son signos vitales continuos en vuelo** y, con n = 4, no se extraen conclusiones causales. La aplicación los usa para mostrar la comparación con rangos de laboratorio y probar los controles de calidad con datos reales.'),
  ...fig('09_nasa_data.jpg', 'Módulo NASA Data con datos reales de OSDR.'));

add(H1('15. Pruebas automatizadas'),
  P(`Todas las pruebas se ejecutaron el ${RUN_DATE}. Las cifras provienen de los archivos de salida guardados en \`docs/academic/final/tests/\`; ninguna se escribió manualmente.`),
  ...table(['Conjunto', 'Herramienta', 'Resultado real'], [
    ['Backend: autenticación, autorización, CRUD, API, seguridad, motor, cuentas demo', 'pytest 9.1.1', `**${TESTS.length} aprobadas, 0 fallidas**`],
    ['Motor de reglas original (frontend)', 'Node.js (`tests/engine.test.js`)', '**10/10 aprobadas**'],
    ['Interfaz E2E con los 3 roles (frontend + API)', 'Playwright + Chrome (`tests/e2e_academic.py`)', `**${E2E.filter(l => l.startsWith('PASS')).length}/${E2E.length} verificaciones aprobadas**, 0 errores JS`],
  ], [4200, 2600, 2226], { caption: 'Resumen de pruebas ejecutadas.' }),
  ...table(['Archivo', 'Pruebas', 'Qué verifica'], Object.keys(perFile).sort().map(f => [`\`${f}\``, String(perFile[f]), testDesc[f] || '']), [2500, 900, 5626], { caption: 'Pruebas pytest por archivo.' }),
  P('Las pruebas de backend usan una base SQLite en **archivo temporal** por prueba (no en memoria), con las mismas restricciones y claves foráneas que producción. La prueba E2E levanta el frontend real compilado y la API Flask en local, y recorre en Chrome el login de cada rol, los diez módulos, los permisos, el registro de mediciones, la cola LOS/AOS, la revisión de alertas, el CRUD de astronautas y misiones y los límites de las cuentas demo.'),
  NOTE('Observación de la auditoría: si se ejecuta pytest en una terminal donde se exportaron `CORS_ORIGINS` o `DATABASE_PATH` para un servidor local, 25 pruebas de API fallan porque toman esa configuración. Las pruebas deben ejecutarse con la configuración por defecto (`env -u CORS_ORIGINS -u DATABASE_PATH python -m pytest`).'),
  ...fig('19_tests_pytest.jpg', 'Salida real de pytest.'),
  ...fig('19_tests_engine_js.jpg', 'Salida real de las pruebas del motor JavaScript.', 600, 360),
  ...fig('19_tests_playwright_e2e.jpg', 'Salida real de la prueba E2E con Playwright (84 verificaciones).', 600, 900),
  NOTE('Las pruebas verifican el comportamiento del software. ASTRA VITAL no ha pasado por validación clínica.'));

add(H1('16. Despliegue'),
  ...table(['Recurso', 'Enlace', 'Verificación (16/11/2026)'], [
    ['Aplicación web (GitHub Pages)', '[https://etner249.github.io/astra-vital/](https://etner249.github.io/astra-vital/)', 'Carga el login; servidor en línea; commit b9da8f8'],
    ['Backend / API (Render)', '[https://astra-vital-academic.onrender.com](https://astra-vital-academic.onrender.com/api/v1/health)', '`/api/v1/health` → status ok; servicio Live, commit 8d6bd9b'],
    ['GitHub frontend', '[https://github.com/Etner249/astra-vital](https://github.com/Etner249/astra-vital)', 'Público; deployment github-pages correcto'],
    ['GitHub backend', '[https://github.com/Etner249/astra-vital-flask-sqlite](https://github.com/Etner249/astra-vital-flask-sqlite)', 'Público; rama main'],
    ['Entrega NASA (congelada)', '[https://etner249.github.io/astra-vital/nasa-2026/](https://etner249.github.io/astra-vital/nasa-2026/)', 'SHA-256 idéntico al commit 8df773b'],
  ], [2100, 3900, 3026], { caption: 'Enlaces del proyecto y su verificación.' }),
  P('El servicio de Render se define con un Blueprint (`render.yaml`): construcción `pip install -r requirements.txt`, arranque `flask --app wsgi bootstrap && gunicorn -c gunicorn.conf.py wsgi:app`, health check y variables de entorno (SECRET_KEY y contraseñas privadas generadas por Render, nunca escritas en el repositorio). GitHub Pages publica la rama `main` del repositorio frontend.'),
  NOTE('**Limitación de persistencia:** el plan gratuito de Render no ofrece disco persistente. SQLite vive en el sistema de archivos efímero de la instancia: cada reinicio, redespliegue o suspensión por inactividad borra la base, y `flask bootstrap` la recrea con datos sintéticos y las cuentas demo. Se verificó en los logs ("No SQLite database… creating a new one"). Para persistencia real se requiere un plan de pago con disco persistente o una base gestionada. La primera petición tras la suspensión puede tardar ~50 s.'),
  ...fig('20a_production_github_pages_login.jpg', 'Aplicación publicada en la URL oficial de GitHub Pages.', 520),
  ...fig('20b_production_render_api_health.jpg', 'API de producción en Render respondiendo `/api/v1/health` (status ok).', 560, 120),
  ...fig('20d_render_service_live.jpg', 'Servicio astra-vital-academic en Render (estado Live).', 520),
  ...fig('20f_github_frontend_repo.jpg', 'Repositorio frontend en GitHub.', 480),
  ...fig('20g_github_backend_repo.jpg', 'Repositorio backend en GitHub.', 480));

add(H1('17. Participación en NASA Space Apps Challenge 2026'),
  ...table(['Dato', 'Valor'], [
    ['Desafío', 'Create Health Monitoring Software for Astronauts on Space Missions'],
    ['Equipo', 'NYXARA NOVA — evento local Trujillo, Perú'],
    ['Integrantes', COVER.members.join(' · ')],
    ['Página oficial del equipo', '[https://www.spaceappschallenge.org/2026/find-a-team/nyxara-nova/](https://www.spaceappschallenge.org/2026/find-a-team/nyxara-nova/)'],
    ['Proyecto', 'ASTRA VITAL — [https://etner249.github.io/astra-vital/](https://etner249.github.io/astra-vital/)'],
    ['Videos', '[Demo 30 s](https://youtu.be/lxITVao2RmQ) · [Presentación completa](https://youtu.be/sz9qzXasEKc)'],
    ['Estado', 'Enviado a evaluación (*Submit for Judging*) el 15/11/2026 a las 16:35 (hora local)'],
    ['Certificado', COVER.certificate ? 'Incluido en el Anexo F' : '[PENDIENTE — certificado oficial a proporcionar por el equipo]'],
  ], [2400, 6626], { caption: 'Datos de la participación.' }),
  ...fig('21a_space_apps_team_page.jpg', 'Página del equipo NYXARA NOVA en el portal de NASA Space Apps.', 480),
  NOTE('ASTRA VITAL es un proyecto independiente: no fue desarrollado, respaldado ni validado por la NASA.'));

add(H1('18. Evidencias visuales'),
  P('Todas las capturas son de la aplicación real. Las de la aplicación en uso se tomaron con Playwright sobre una copia local del mismo código publicado (frontend commit b9da8f8 y backend main), para iniciar sesión con las cuentas demo sin escribir contraseñas en el sitio público; las de producción se tomaron directamente de las URLs públicas. Los archivos originales están en `docs/academic/final/evidence/`.'),
  ...table(['Nº', 'Evidencia solicitada', 'Archivo(s)', 'Sección'], [
    ['1', 'Inicio de sesión', '01_login, 20a_production_github_pages_login', '6, 16'], ['2', 'Cuentas de demostración', '02_demo_accounts, 02b_project_briefing', '10'],
    ['3', 'Dashboard', '03_dashboard_admin', '12'], ['4', 'Registro de mediciones', '04a, 04b', '12, 13'], ['5', 'Perfil del astronauta', '05_astronaut_profile', '12'],
    ['6', 'Interactive Body', '06_interactive_body', '12'], ['7', 'Health Intelligence', '07_health_intelligence', '12'], ['8', 'Mission Risk Center', '08_mission_risk_center', '12'],
    ['9', 'NASA Data', '09_nasa_data', '12, 14'], ['10', 'Ground Console', '10_ground_console', '12'], ['11', 'Sync & Reports', '11a, 11b', '12'],
    ['12', 'Gestión de astronautas', '12a, 18a–18e', '11, 12'], ['13', 'Gestión de misiones', '13_missions_management', '12'], ['14', 'Base de datos de mediciones', '14a, 14b', '12'],
    ['15', 'Revisión de alertas', '15a, 15b', '12'], ['16', 'Gestión de usuarios', '16_users_admin_demo_read_only', '10, 12'], ['17', 'Auditoría', '17_audit_log', '12'],
    ['18', 'Operaciones CRUD', '18a–18e, 14b, 14c', '11'], ['19', 'Pruebas automatizadas', '19_tests_*', '15'], ['20', 'Despliegue', '20a–20h', '16'],
  ], [600, 2700, 3900, 1826], { caption: 'Correspondencia entre evidencias solicitadas y capturas.' }),
  ...fig('11b_sync_reports_after_sync.jpg', 'Sync & Reports después de sincronizar con la API.'),
  ...fig('15a_alert_review_admin.jpg', 'Alert Review (vista del Administrador).'),
  ...fig('19d_operator_records_no_edit_delete.jpg', 'Operador: la base de mediciones no muestra botones de edición ni eliminación.'),
  ...fig('19e_operator_profile_read_only.jpg', 'Operador: perfil de solo lectura.'),
  ...fig('02b_project_briefing.jpg', 'Project Briefing en la pantalla de acceso.', 420),
  ...fig('20c_login_mobile.jpg', 'Pantalla de acceso en móvil (390 px).', 260, 560));

add(H1('19. Resultados'),
  ...table(['Requisito del curso', 'Resultado', 'Evidencia'], [
    ['1. Desafío NASA, problema y solución', 'Cumplido', 'Secciones 2–6'],
    ['2. Aplicación web Flask con interfaz modular', 'Cumplido: API Flask + interfaz Flask/Jinja + SPA con 15 módulos', 'Secciones 7, 12'],
    ['3. SQLite con CRUD', 'Cumplido: 7 tablas, CRUD de 5 entidades', 'Secciones 9, 11'],
    ['4. Registro, login, logout y roles', 'Cumplido: 3 roles en backend, tokens y sesiones', 'Sección 10'],
    ['5. Pruebas automatizadas', `Cumplido: ${TESTS.length} pytest + 10 motor JS + ${E2E.length} E2E`, 'Sección 15'],
    ['6. GitHub y Render', 'Cumplido (Render Free sin persistencia)', 'Sección 16'],
    ['7. Certificado NASA', COVER.certificate ? 'Cumplido' : 'Participación verificada; certificado pendiente de adjuntar', 'Sección 17'],
  ], [3200, 3800, 2026], { caption: 'Cumplimiento de los siete requisitos.' }));

add(H1('20. Limitaciones'),
  ...B(['Prototipo educativo: no es un dispositivo médico certificado, no diagnostica ni reemplaza a médicos de vuelo o protocolos oficiales; no tiene validación clínica.',
    'Los datos se ingresan manualmente; no hay conexión con sensores médicos certificados ni con sistemas reales de una nave o de la NASA.',
    'El retardo de comunicación y las ventanas AOS/LOS son simulados.',
    'Render Free: SQLite se borra al reiniciar, redesplegar o suspender; la primera carga tras inactividad tarda hasta ~50 s.',
    'SQLite admite un solo escritor a la vez: adecuado para un prototipo con pocos usuarios, no para alta concurrencia.',
    'El límite de intentos de login se guarda en memoria por proceso (no compartido entre workers).',
    'Las convenciones del motor (2 DE, 7 días, 36 h) y los umbrales requieren validación clínica.']));

add(H1('21. Conclusiones'),
  ...NL(['Se desarrolló una aplicación web con **Python Flask y SQLite** que cumple los requisitos del curso: base de datos relacional con restricciones, CRUD completo, autenticación, tres roles verificados en el backend y una API REST documentada.',
    'La integración con GitHub Pages mantuvo la URL oficial y los diez módulos originales, y añadió cinco módulos de gestión sin alterar la copia entregada a la NASA.',
    'El uso de tokens Bearer y CORS restringido resolvió la comunicación entre dominios de forma segura y compatible con navegadores que bloquean cookies de terceros.',
    `Las pruebas automatizadas (${TESTS.length} de backend, 10 del motor y ${E2E.length} verificaciones E2E) pasaron sin fallos en la ejecución documentada.`,
    'El despliegue en Render demuestra el funcionamiento en la nube, pero su plan gratuito no garantiza persistencia; esta limitación se documentó y se verificó.']));

add(H1('22. Recomendaciones'),
  ...B(['Migrar a un plan de Render con disco persistente o a PostgreSQL gestionado para conservar los datos.',
    'Mover el límite de intentos de login a un almacén compartido (p. ej. Redis) y añadir bloqueo progresivo.',
    'Validar umbrales y convenciones del motor con profesionales de la salud.',
    'Incorporar integración opcional con dispositivos de medición y notificaciones.',
    'Automatizar pytest y Playwright en GitHub Actions en cada cambio.']));

add(H1('23. Referencias bibliográficas'),
  ...NL(['NASA Space Apps Challenge. (2026). *Create Health Monitoring Software for Astronauts on Space Missions*. [https://www.spaceappschallenge.org/](https://www.spaceappschallenge.org/)',
    'NASA Human Research Program. (s. f.). *5 Hazards of Human Spaceflight*. [https://www.nasa.gov/hrp/hazards/](https://www.nasa.gov/hrp/hazards/)',
    'NASA Open Science Data Repository. *OSD-575: Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays*. [https://osdr.nasa.gov/bio/repo/data/studies/OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575)',
    'NASA Open Science Data Repository. *OSD-569: Inspiration4 whole blood measurements (incl. CBC)*. [https://osdr.nasa.gov/bio/repo/data/studies/OSD-569](https://osdr.nasa.gov/bio/repo/data/studies/OSD-569)',
    'Whelton, P. K., et al. (2018). 2017 ACC/AHA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. *Hypertension, 71*, e13–e115.',
    'World Health Organization. (2011). *Pulse Oximetry Training Manual*.',
    'Centers for Disease Control and Prevention. Definición de fiebre (≥ 38,0 °C).',
    'Watson, N. F., et al. (2015). Recommended amount of sleep for a healthy adult. *Sleep, 38*(6).',
    'Barger, L. K., et al. (2014). Prevalence of sleep deficiency and use of hypnotic drugs in astronauts. *The Lancet Neurology, 13*(9).',
    'Samn, S. W., & Perelli, L. P. (1982). *Estimating aircrew fatigue*. USAF School of Aerospace Medicine.',
    'American Diabetes Association. *Standards of Care in Diabetes* (clasificación de hipoglucemia).',
    'Pallets Projects. *Flask documentation*. [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)',
    'SQLAlchemy. *SQLAlchemy 2.0 documentation*. [https://docs.sqlalchemy.org/](https://docs.sqlalchemy.org/)',
    'SQLite. *SQLite documentation*. [https://sqlite.org/docs.html](https://sqlite.org/docs.html)',
    'Render. *Render documentation*. [https://render.com/docs](https://render.com/docs)',
    'Microsoft. *Playwright for Python*. [https://playwright.dev/python/](https://playwright.dev/python/)']));

add(H1('Anexos'),
  H2('Anexo A. Esquema SQL real'), P('Extraído de la base creada por `flask bootstrap` (archivo `docs/academic/schema.sql`).'), ...CODE(SCHEMA),
  H2('Anexo B. Ejecución local'), ...CODE(['git clone https://github.com/Etner249/astra-vital-flask-sqlite.git', 'cd astra-vital-flask-sqlite', 'python -m venv .venv && source .venv/bin/activate', 'pip install -r requirements.txt', 'flask --app wsgi bootstrap      # tablas + datos sintéticos + cuentas demo', 'flask --app wsgi run --port 5056', 'python -m pytest -v             # 136 pruebas', '', '# Frontend (repositorio astra-vital)', 'AV_API_BASE=http://127.0.0.1:5056/api/v1 python3 build.py', 'python3 tests/e2e_academic.py http://127.0.0.1:8080/astra-vital/ shots/'].join('\n')),
  H2('Anexo C. Lista de pruebas pytest'), ...CODE(TESTS.map(([f, t]) => `${f}::${t}`).join('\n')),
  H2('Anexo D. Verificaciones E2E (Playwright)'), ...CODE(E2E.join('\n')),
  H2('Anexo E. Interfaz Flask (Jinja) en Render'), P('Además de la API, el backend ofrece su propia interfaz HTML en `https://astra-vital-academic.onrender.com/login`.'), ...fig('20e_render_flask_login.jpg', 'Interfaz Flask en Render.', 480),
  H2('Anexo F. Certificado NASA Space Apps Challenge 2026'),
  ...(COVER.certificate ? fig(COVER.certificate, 'Certificado oficial de participación.') : [NOTE('**PENDIENTE:** el certificado oficial debe ser proporcionado por el equipo (descargable desde el perfil del participante en spaceappschallenge.org). No se reconstruye ni se genera.')]));

// ======================================================= DOCUMENT
const doc = new Document({
  creator: 'Equipo NYXARA NOVA', title: 'ASTRA VITAL — Trabajo final (Flask + SQLite)', description: 'Trabajo final del curso — ASTRA VITAL Academic Edition',
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 32, bold: true, color: NAVY }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: '36D6E7', space: 4 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 26, bold: true, color: BLUE }, paragraph: { spacing: { before: 220, after: 100 }, keepNext: true, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 23, bold: true, color: '24324A' }, paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ]
  },
  numbering: { config: [
    { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: 'num', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children: cover },
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 }, pageNumbers: { start: 1 } } },
      headers: { default: new Header({ children: [new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'C9D3E0', space: 2 } }, tabStops: [{ type: TabStopType.RIGHT, position: CW }], children: [new TextRun({ text: 'ASTRA VITAL — Trabajo final · Python Flask + SQLite', size: 16, color: GREY }), new TextRun({ text: '\tEquipo NYXARA NOVA', size: 16, color: GREY })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Página ', size: 16, color: GREY }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREY })] })] }) },
      children: [
        new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 200 }, children: [new TextRun({ text: 'Índice', bold: true, size: 32, color: NAVY })] }),
        new TableOfContents('Índice', { hyperlink: true, headingStyleRange: '1-2' }),
        ...body
      ] }
  ]
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(path.join(__dirname, 'ASTRA_VITAL_TRABAJO_FINAL.raw.docx'), buf); console.log('docx', buf.length, 'bytes; figures', figN, 'tables', tabN); });
