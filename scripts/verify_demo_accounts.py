"""End-to-end check of the public demo accounts through the real login page (browser, Playwright + Chrome).

Usage:  python3 scripts/verify_demo_accounts.py http://127.0.0.1:5055 [screenshot-prefix]
For each account it clicks "Usar esta cuenta" on the login page (the credentials come from the page itself),
signs in, checks the role shown, probes role-restricted pages and the demo safety limits, then signs out."""
import pathlib
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "22"
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs/academic/evidence"
EXPECT = {  # path -> HTTP status expected per role
    "ADMINISTRADOR": {"role": "Administrator", "/users": 200, "/users/new": 403, "/audit": 200, "/reports": 200, "/astronauts/new": 200},
    "MÉDICO / ESPECIALISTA": {"role": "Doctor", "/users": 403, "/users/new": 403, "/audit": 403, "/reports": 200, "/astronauts/new": 403},
    "OPERADOR": {"role": "Operator", "/users": 403, "/users/new": 403, "/audit": 403, "/reports": 403, "/astronauts/new": 403},
}
SLUG = {"ADMINISTRADOR": "admin", "MÉDICO / ESPECIALISTA": "doctor", "OPERADOR": "operator"}
ok = True


def shot(pg, name, full=False):
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / f"{PREFIX}_{name}.png"), full_page=full)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    pg = ctx.new_page()
    pg.goto(BASE + "/login")
    shot(pg, "login_evaluator_access", True)
    # copy button really copies (clipboard API on localhost / https)
    pg.locator(".demo-acc").first.locator("button.copy").first.click()
    copied = pg.evaluate("navigator.clipboard.readText()")
    shown = pg.locator(".demo-acc").first.locator("code").first.inner_text()
    print(f"copy button: clipboard={copied!r} matches page={copied == shown}")
    ok &= copied == shown
    m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
    m.goto(BASE + "/login"); m.wait_for_timeout(300)
    m.screenshot(path=str(OUT / f"{PREFIX}_login_mobile.png"), full_page=True); m.close()

    for label, exp in EXPECT.items():
        pg.goto(BASE + "/login")
        card = pg.locator(".demo-acc", has=pg.locator(".role-badge", has_text=label))
        email = card.get_attribute("data-email")
        card.locator(".use-acc").click()
        if label == "ADMINISTRADOR":
            shot(pg, "login_account_selected")
        pg.click("#submit"); pg.wait_for_load_state()
        body = pg.inner_text("body")
        signed = f"Signed in as  {exp['role']}" in body.replace("\xa0", " ") or exp["role"] in pg.inner_text(".topbar")
        demo_pill = "PUBLIC DEMO ACCOUNT" in body
        shot(pg, f"dashboard_{SLUG[label]}")
        res = {}
        for path in ("/users", "/users/new", "/audit", "/reports", "/astronauts/new"):
            r = pg.goto(BASE + path)
            res[path] = r.status
            if label == "ADMINISTRADOR" and path == "/users":
                shot(pg, "admin_users_read_only")
            if label == "OPERADOR" and path == "/reports":
                shot(pg, "operator_reports_403")
        good = signed and demo_pill and all(res[k] == exp[k] for k in res)
        ok &= good
        print(f"{label:22} {email:34} login={'OK' if signed else 'FAIL'} demo_badge={demo_pill} "
              + " ".join(f"{k}={v}" for k, v in res.items()) + f"  -> {'PASS' if good else 'FAIL'}")
        pg.goto(BASE + "/dashboard")
        pg.locator("form[action$='/logout'] button").first.click(); pg.wait_for_load_state()
    b.close()
print("ALL PASS" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
