"""Build docs/academic/ASTRA_VITAL_TRABAJO_FINAL.pdf from the academic docs and real evidence.

Usage:  python scripts/build_final_pdf.py
Requires: weasyprint, markdown, pypdf; poppler (pdftoppm) to render the NASA certificate pages.
Cover data comes from docs/academic/cover.json; missing fields are printed as PENDIENTE (never invented).
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "academic"
EVID = DOCS / "evidence"
OUT = DOCS / "ASTRA_VITAL_TRABAJO_FINAL.pdf"
CERT = EVID / "nasa-participation-certificate.pdf"
LOGO = ROOT / "app" / "static" / "img" / "astra-vital-logo.svg"
MD_EXT = ["tables", "fenced_code", "sane_lists"]
pending = []


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def include(name, skip=()):
    text = (DOCS / name).read_text(encoding="utf-8")
    text = re.sub(r"\A# .*\n", "", text)                      # drop H1
    parts = re.split(r"(?m)^(?=## )", text)
    keep = [p for p in parts if not (p.startswith("## ") and p[3:].split("\n")[0].strip() in skip)]
    text = "".join(keep)
    text = re.sub(r"(?m)^### ", "#### ", text)
    text = re.sub(r"(?m)^## ", "### ", text)
    text = re.sub(r"(?m)^\*\*Herramienta:\*\*", "**Herramienta:**", text)
    text = re.sub(r"`evidence/([^`]+)`", r"`evidence/\1`", text)
    return text


fig_no = [0]


def figure(spec):
    name, caption, *opt = spec.split("|")
    opt = opt[0] if opt else ""
    p = EVID / name
    if not p.exists():
        if opt == "optional":
            pending.append(f"Evidencia {name}")
            return (f'<div class="pending">Captura pendiente: <b>{html.escape(caption)}</b> '
                    f'({name}). Se incorporará cuando el propietario de la cuenta inicie sesión en el despliegue.</div>')
        sys.exit(f"Missing evidence {name}")
    fig_no[0] += 1
    cls = {"narrow": "fig narrow", "tall": "fig tall", "half": "fig half"}.get(opt, "fig")
    return (f'<figure class="{cls}"><img src="{p.as_uri()}"/><figcaption>Figura {fig_no[0]}. '
            f'{html.escape(caption)} <span class="src">({name})</span></figcaption></figure>')


def certificate():
    if not CERT.exists():
        pending.append("Certificado NASA (evidence/nasa-participation-certificate.pdf)")
        return ('<div class="pending"><b>PENDIENTE:</b> el certificado oficial de participación en el NASA Space Apps '
                'Challenge 2026 debe ser proporcionado por el equipo (archivo original emitido por la organización). '
                'No se reconstruye ni se genera.</div>')
    tmp = EVID / "_tmp"
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("cert-*"):
        f.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "150", str(CERT), str(tmp / "cert")], check=True)
    pages = sorted(tmp.glob("cert-*.png"))
    out = ['<p>Reproducción del certificado original emitido por NASA Space Apps Challenge 2026, sin modificaciones '
           '(archivo <code>docs/academic/evidence/nasa-participation-certificate.pdf</code>).</p>']
    for i, pg in enumerate(pages, 1):
        out.append(f'<figure class="fig cert"><img src="{pg.as_uri()}"/><figcaption>Certificado NASA Space Apps '
                   f'Challenge 2026 — página {i} de {len(pages)}</figcaption></figure>')
    return "\n".join(out)


def body():
    src = (DOCS / "TRABAJO_FINAL_CONTENT.md").read_text(encoding="utf-8")

    def inc(m):
        name, *rest = m.group(1).split("|")
        skip = tuple(s.strip() for s in rest[0][5:].split(",")) if rest and rest[0].startswith("skip=") else ()
        return include(name, skip)

    src = src.replace("{{cert}}", "\n\nCERT_PLACEHOLDER\n\n")
    src = re.sub(r"\{\{fig:([^}]+)\}\}", lambda m: "\n\nFIG_" + str(abs(hash(m.group(1)))) + "\n\n", src)
    raw_chapters = re.split(r"(?m)^# ", src)[1:]
    raw_chapters = [re.sub(r"\{\{include:([^}]+)\}\}", inc, ch) for ch in raw_chapters]
    figs = {"FIG_" + str(abs(hash(s))): figure(s) for s in re.findall(r"\{\{fig:([^}]+)\}\}",
                                                                       (DOCS / "TRABAJO_FINAL_CONTENT.md").read_text(encoding="utf-8"))}
    chapters, toc = [], []
    for n, chunk in enumerate(raw_chapters, 1):
        title, rest = chunk.split("\n", 1)
        sid = f"c{n}-{slug(title)}"
        sub = []
        def h2(m):
            t = m.group(1).strip()
            k = f"{sid}-{slug(t)}"
            sub.append((t, k))
            return f'<h2 id="{k}">{n}.{len(sub)} {html.escape(t)}</h2>'
        h = markdown.markdown(rest, extensions=MD_EXT)
        h = re.sub(r"<h3>(.*?)</h3>", lambda m: f"<h2>{m.group(1)}</h2>", h)
        h = re.sub(r"<h4>(.*?)</h4>", lambda m: f"<h3>{m.group(1)}</h3>", h)
        h = re.sub(r"<h2>(.*?)</h2>", h2, h)
        h = re.sub(r'(?<!["=>])(https?://[^\s<)]+)', r'<a href="\1">\1</a>', h)
        for k, v in figs.items():
            h = h.replace(f"<p>{k}</p>", v)
        h = h.replace("<p>CERT_PLACEHOLDER</p>", certificate())
        chapters.append(f'<section class="chapter" id="{sid}"><h1><span class="num">{n}.</span> {html.escape(title)}</h1>{h}</section>')
        toc.append((n, title, sid, sub))
    return chapters, toc


def cover(c):
    def val(key, label):
        v = c.get(key)
        if not v:
            pending.append(label)
            return f'<span class="pend">PENDIENTE — {label.lower()}</span>'
        return html.escape(v)
    members = "".join(f"<li>{html.escape(m)}</li>" for m in c["members"])
    return f"""
<section class="cover">
  <div class="band">
    <div class="uni">{val('university', 'Universidad')}</div>
    <div class="fac">{val('faculty', 'Facultad')}</div>
  </div>
  <div class="center">
    <div class="course-l">Curso</div>
    <div class="course">{val('course', 'Nombre del curso')}</div>
    <div class="logo"><img src="{LOGO.as_uri()}"/></div>
    <h1 class="title">ASTRA VITAL</h1>
    <div class="subtitle">Sistema web de monitoreo de salud de astronautas<br/>Edición académica — Python Flask + SQLite</div>
    <div class="origin">Basado en el proyecto del equipo NYXARA NOVA para el NASA Space Apps Challenge 2026</div>
  </div>
  <table class="meta">
    <tr><th>Integrantes<br/><small>Equipo {html.escape(c['team'])}</small></th><td><ul>{members}</ul></td></tr>
    <tr><th>Docente</th><td>{val('professor', 'Docente')}</td></tr>
    <tr><th>Ciclo / sección</th><td>{val('cycle_section', 'Ciclo y sección')}</td></tr>
  </table>
  <div class="place">{html.escape(c['city_date'])}</div>
</section>"""


def toc_html(toc):
    rows = []
    for n, t, sid, sub in toc:
        rows.append(f'<li class="l1"><a href="#{sid}">{n}. {html.escape(t)}</a></li>')
        for i, (st, k) in enumerate(sub, 1):
            rows.append(f'<li class="l2"><a href="#{k}">{n}.{i} {html.escape(st)}</a></li>')
    return f'<section class="toc"><h1 class="toch">Índice</h1><ul>{"".join(rows)}</ul></section>'


CSS = """
@page { size: A4; margin: 24mm 20mm 22mm 22mm;
  @top-left { content: "ASTRA VITAL — Edición Académica (Flask + SQLite)"; font: 8pt Inter; color: #5b6b82; border-bottom: .4pt solid #c9d3e0; vertical-align: bottom; padding-bottom: 3pt; }
  @top-right { content: string(chap); font: 8pt Inter; color: #5b6b82; border-bottom: .4pt solid #c9d3e0; vertical-align: bottom; padding-bottom: 3pt; }
  @bottom-left { content: "Equipo NYXARA NOVA · NASA Space Apps Challenge 2026"; font: 8pt Inter; color: #5b6b82; }
  @bottom-right { content: "Página " counter(page) " de " counter(pages); font: 8pt Inter; color: #5b6b82; } }
@page cover { margin: 0; @top-left{content:none} @top-right{content:none} @bottom-left{content:none} @bottom-right{content:none} }
html { font-family: "Source Serif 4", "Noto Serif", "DejaVu Serif", serif; font-size: 10.5pt; line-height: 1.5; color: #1b2433; }
h1, h2, h3, th, figcaption, .toc, .cover { font-family: Inter, "DejaVu Sans", sans-serif; }
.cover { page: cover; height: 297mm; position: relative; background: #fff; }
.cover .band { background: #0b1526; color: #e8eef8; padding: 22mm 22mm 12mm; }
.cover .uni { font-size: 17pt; font-weight: 700; letter-spacing: .3pt; }
.cover .fac { font-size: 11pt; color: #9fb3cf; margin-top: 3pt; }
.cover .center { text-align: center; padding: 16mm 22mm 0; }
.course-l { font-size: 8.5pt; text-transform: uppercase; letter-spacing: 1.5pt; color: #5b6b82; }
.course { font-size: 14pt; font-weight: 600; margin-top: 2pt; }
.cover .logo { margin: 14mm auto 4mm; width: 92mm; background: #0b1526; border-radius: 6pt; padding: 6mm 8mm; }
.cover .logo img { width: 100%; }
.cover .title { font-size: 30pt; letter-spacing: 3pt; margin: 4mm 0 2mm; color: #0b1526; }
.cover .subtitle { font-size: 12.5pt; color: #24324a; }
.cover .origin { font-size: 9.5pt; color: #5b6b82; margin-top: 5mm; }
.cover table.meta { margin: 14mm 22mm 0; width: calc(100% - 44mm); border-collapse: collapse; font-size: 10.5pt; }
.cover table.meta th { text-align: left; width: 52mm; vertical-align: top; color: #5b6b82; font-weight: 600; padding: 4pt 0; border-top: .5pt solid #d5dde8; background: none; }
.cover table.meta td { padding: 4pt 0; border-top: .5pt solid #d5dde8; }
.cover table.meta ul { margin: 0; padding: 0; list-style: none; }
.cover .place { position: absolute; bottom: 18mm; width: 100%; text-align: center; font-size: 10pt; color: #5b6b82; }
.pend { color: #b42318; font-weight: 600; }
.toc { page-break-before: always; page-break-after: always; }
.toch { font-size: 18pt; color: #0b1526; border-bottom: 1.2pt solid #36d6e7; padding-bottom: 4pt; }
.toc ul { list-style: none; padding: 0; }
.toc li a { color: #1b2433; text-decoration: none; }
.toc li a::after { content: leader(".") target-counter(attr(href), page); color: #5b6b82; }
.toc li.l1 { font-weight: 600; margin-top: 5pt; font-size: 10.5pt; }
.toc li.l2 { padding-left: 14pt; font-size: 9.5pt; color: #3a4a62; }
.chapter { page-break-before: always; }
.chapter > h1 { string-set: chap content(text); font-size: 17pt; color: #0b1526; border-bottom: 1.2pt solid #36d6e7; padding-bottom: 4pt; margin: 0 0 10pt; }
.chapter > h1 .num { color: #1e6fd9; }
h2 { font-size: 12.5pt; color: #0b1526; margin: 14pt 0 4pt; page-break-after: avoid; }
h3 { font-size: 10.5pt; color: #24324a; margin: 10pt 0 3pt; page-break-after: avoid; }
p { margin: 0 0 6pt; text-align: justify; }
a { color: #1e6fd9; text-decoration: none; word-break: break-all; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.3pt; background: #eef2f7; padding: 0 2pt; border-radius: 2pt; }
pre { background: #0f1b2e; color: #e8eef8; padding: 7pt 9pt; border-radius: 4pt; font-size: 8pt; white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.6pt; page-break-inside: auto; }
th { background: #0b1526; color: #e8eef8; text-align: left; padding: 4pt 5pt; font-weight: 600; }
td { border-bottom: .5pt solid #d5dde8; padding: 3.5pt 5pt; vertical-align: top; }
tr { page-break-inside: avoid; }
tr:nth-child(even) td { background: #f5f8fb; }
ul, ol { margin: 0 0 6pt; padding-left: 16pt; }
li { margin-bottom: 2pt; }
figure.fig { margin: 8pt 0 12pt; page-break-inside: avoid; text-align: center; }
figure.fig img { max-width: 100%; max-height: 112mm; border: .5pt solid #c9d3e0; }
figure.tall img { max-height: 190mm; }
figure.narrow img { max-height: 150mm; }
figure.half img { max-height: 95mm; }
figure.cert img { max-height: 225mm; }
figcaption { font-size: 8.5pt; color: #3a4a62; margin-top: 3pt; }
figcaption .src { color: #8392a7; }
.pending { border: 1pt dashed #b42318; color: #7a271a; background: #fef3f2; padding: 8pt 10pt; border-radius: 4pt; font-family: Inter, sans-serif; font-size: 9.5pt; margin: 8pt 0; }
"""


def main():
    c = json.loads((DOCS / "cover.json").read_text(encoding="utf-8"))
    cov = cover(c)
    chapters, toc = body()
    doc = f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>ASTRA VITAL — Trabajo final</title><style>{CSS}</style></head><body>{cov}{toc_html(toc)}{"".join(chapters)}</body></html>'
    HTML(string=doc, base_url=str(ROOT)).write_pdf(OUT)
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(OUT)
    w = PdfWriter(clone_from=r)
    w.add_metadata({"/Title": "ASTRA VITAL — Edición Académica (Flask + SQLite): Trabajo final",
                    "/Author": "Equipo NYXARA NOVA: " + ", ".join(c["members"]),
                    "/Subject": "Aplicación web de monitoreo de salud de astronautas — UPRIT"})
    with open(OUT, "wb") as f:
        w.write(f)
    print(f"{OUT} — {len(r.pages)} pages")
    for p in sorted(set(pending)):
        print("PENDING:", p)


if __name__ == "__main__":
    main()
