"""Opens the generated DOCX in LibreOffice (UNO), updates the table of contents and all fields,
saves the final DOCX (with the populated index) and exports the PDF from the same document."""
import os, subprocess, sys, tempfile, time, pathlib
sys.path.insert(0, '/root/.claude/skills/synced/7460e0cb-ce80-40ef-b094-abf6bf527af1_f1ea0cf2-b3fb-4290-84f7-ebaef814a85b/docx/scripts')
from office.soffice import get_soffice_env
import uno
from com.sun.star.beans import PropertyValue

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / 'ASTRA_VITAL_TRABAJO_FINAL.raw.docx'
OUT_DOCX = HERE.parent / 'ASTRA_VITAL_TRABAJO_FINAL.docx'
OUT_PDF = HERE.parent / 'ASTRA_VITAL_TRABAJO_FINAL.pdf'

def prop(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p

profile = tempfile.mkdtemp(prefix='lo_uno_')
pipe = f'avpipe{os.getpid()}'
proc = subprocess.Popen(['soffice', f'-env:UserInstallation=file://{profile}', '--headless', '--invisible', '--nologo', '--norestore',
                         f'--accept=pipe,name={pipe};urp;'], env=get_soffice_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ctx = None
for _ in range(60):
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        ctx = resolver.resolve(f'uno:pipe,name={pipe};urp;StarOffice.ComponentContext'); break
    except Exception:
        time.sleep(1)
assert ctx, 'could not connect to soffice'
desktop = ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(SRC)), '_blank', 0, (prop('Hidden', True),))
for _ in range(2):  # twice: page numbers settle after the index is filled
    idx = doc.getDocumentIndexes()
    for i in range(idx.getCount()):
        idx.getByIndex(i).update()
    doc.getTextFields().refresh()
    doc.refresh()
print('indexes updated:', doc.getDocumentIndexes().getCount())
doc.storeToURL(uno.systemPathToFileUrl(str(OUT_DOCX)), (prop('FilterName', 'MS Word 2007 XML'),))
doc.storeToURL(uno.systemPathToFileUrl(str(OUT_PDF)), (prop('FilterName', 'writer_pdf_Export'), prop('FilterData', uno.Any('[]com.sun.star.beans.PropertyValue', tuple([prop('UseTaggedPDF', True), prop('ExportBookmarks', True), prop('Quality', 90)]))) ))
doc.close(True)
try: desktop.terminate()
except Exception: pass
proc.wait(timeout=30)
print(OUT_DOCX, OUT_DOCX.stat().st_size); print(OUT_PDF, OUT_PDF.stat().st_size)
