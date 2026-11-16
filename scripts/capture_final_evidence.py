"""Captures REAL screenshots of the ASTRA VITAL academic edition (GitHub Pages frontend build + Flask API)
for the final report. Runs against a local copy of the published code (same commits as production) so the
public demo accounts can be used without typing credentials into the public site.

Usage: python3 scripts/capture_final_evidence.py http://127.0.0.1:8080/astra-vital/ docs/academic/final/evidence
"""
import pathlib
import sys
import time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/") + "/"
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
STAMP = time.strftime("%H%M")


def shot(pg, name, full=False, el=None):
    pg.wait_for_timeout(450)
    path = str(OUT / f"{name}.png")
    (pg.locator(el).first.screenshot(path=path) if el else pg.screenshot(path=path, full_page=full))
    print("saved", name)


def seen(pg):
    pg.evaluate("document.querySelectorAll('.toast').forEach(t => t.setAttribute('data-seen','1'))")


def toast(pg):
    pg.wait_for_selector(".toast:not([data-seen])", timeout=60000)
    t = pg.locator(".toast:not([data-seen])").last.inner_text(); return t


def go(pg, v):
    seen(pg)
    pg.evaluate(f"location.hash = '#{v}'")
    pg.wait_for_function(f"() => document.querySelector('nav a.active') && document.querySelector('nav a.active').dataset.v === '{v}'", timeout=30000)
    pg.wait_for_function("() => { const e = document.querySelector('#view'); return e && e.querySelector('.card,.hazard') && !/^Loading/.test((e.querySelector('.empty')||{}).textContent||''); }", timeout=60000)
    pg.wait_for_timeout(400)


def login(pg, role):
    pg.goto(BASE); pg.wait_for_selector(f".demo-acc.role-{role} .use-acc", timeout=60000)
    pg.click(f".demo-acc.role-{role} .use-acc"); pg.click("#lbtn"); pg.wait_for_selector(".app nav", timeout=60000); pg.wait_for_timeout(600)


def logout(pg):
    pg.click("#logout"); pg.wait_for_selector("#lf")


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.25)
    # 1-2 login + demo accounts + briefing
    pg.goto(BASE); pg.wait_for_selector(".demo-acc", timeout=60000); pg.wait_for_selector("#srv.ok")
    shot(pg, "01_login")
    shot(pg, "02_demo_accounts", el=".evaluator")
    pg.click("#b-architecture summary"); pg.click("#b-real summary"); pg.wait_for_timeout(300)
    shot(pg, "02b_project_briefing", el=".briefing")
    # wrong credentials
    pg.fill("#email", "nobody@example.com"); pg.fill("#password", "wrong-password-1"); pg.click("#lbtn")
    pg.wait_for_function("() => document.querySelector('#lerr').textContent.length > 0")
    shot(pg, "02c_login_error", el=".login-card")

    # ---------------- administrator
    login(pg, "admin")
    shot(pg, "03_dashboard_admin", full=True)
    go(pg, "log"); pg.select_option("#metric", "bp"); pg.fill("#val", "142"); pg.fill("#val2", "88"); pg.fill("#note", "Evidence: after EVA simulation")
    shot(pg, "04a_log_measurement_form")
    seen(pg); pg.click("#f button[type=submit]"); t = toast(pg); print("  log:", t[:80])
    shot(pg, "04b_log_measurement_saved")
    go(pg, "profile"); shot(pg, "05_astronaut_profile", full=True)
    go(pg, "body"); pg.click("g.zone[data-s=cardio]"); pg.wait_for_timeout(400); shot(pg, "06_interactive_body", full=True)
    go(pg, "alerts"); pg.locator(".alert.priority .head").first.click(); shot(pg, "07_health_intelligence", full=True)
    go(pg, "risk"); shot(pg, "08_mission_risk_center", full=True)
    go(pg, "nasa"); shot(pg, "09_nasa_data", full=True)
    go(pg, "ground"); pg.wait_for_function("() => !document.querySelector('#galerts').innerText.includes('Loading')"); shot(pg, "10_ground_console", full=True)
    go(pg, "sync"); pg.click("#link"); pg.wait_for_timeout(400)
    go(pg, "log"); pg.select_option("#metric", "sleep"); pg.fill("#val", "6.2"); seen(pg); pg.click("#f button[type=submit]"); toast(pg)
    go(pg, "sync"); shot(pg, "11a_sync_los_queue")
    pg.click("#link"); pg.wait_for_timeout(400); seen(pg); pg.click("#sync"); print("  sync:", toast(pg)); shot(pg, "11b_sync_reports_after_sync", full=True)
    # CRUD astronauts
    code = f"AV-EVID-{STAMP}"
    go(pg, "crew"); shot(pg, "12a_crew_and_missions_list", full=True)
    pg.click("#anew"); pg.wait_for_selector("#af")
    pg.fill("#af input[name=code]", code); pg.fill("#af input[name=full_name]", "Evidence Crew Member (fictional)"); pg.fill("#af input[name=role_on_board]", "Payload Specialist")
    pg.fill("#af input[name=demo_age]", "38"); pg.select_option("#af select[name=mission_id]", index=1)
    shot(pg, "18a_crud_create_astronaut_form", full=True)
    seen(pg); pg.click("#af button.primary"); print("  create:", toast(pg)); pg.wait_for_selector(f"tr:has-text('{code}')")
    shot(pg, "18b_crud_read_astronaut_created", full=True)
    pg.locator("tr", has_text=code).locator("[data-edit]").click(); pg.wait_for_selector("#af")
    pg.fill("#af input[name=role_on_board]", "Payload Specialist & Medical Backup"); pg.select_option("#af select[name=status]", "returned")
    seen(pg); pg.click("#af button.primary"); print("  update:", toast(pg)); pg.wait_for_selector("tr:has-text('Medical Backup')")
    shot(pg, "18c_crud_update_astronaut", full=True)
    btn = pg.locator("tr", has_text=code).locator("[data-del]"); btn.click(); pg.wait_for_timeout(200)
    shot(pg, "18d_crud_delete_confirmation", el=f"tr:has-text('{code}')")
    seen(pg); pg.locator("tr", has_text=code).locator("[data-del]").click(); print("  delete:", toast(pg)); pg.wait_for_timeout(800)
    shot(pg, "18e_crud_deleted")
    # missions
    mcode = f"AV-MARS-{STAMP}"
    pg.click("#mnew"); pg.wait_for_selector("#mf"); pg.fill("#mf input[name=code]", mcode); pg.fill("#mf input[name=name]", "Mars transit analog (fictional)")
    pg.select_option("#mf select[name=environment]", "mars"); pg.fill("#mf input[name=duration_days]", "500")
    seen(pg); pg.click("#mf button.primary"); toast(pg); pg.wait_for_selector(f"tr:has-text('{mcode}')")
    pg.locator(".card", has_text="Missions (").first.scroll_into_view_if_needed(); shot(pg, "13_missions_management", el=".card:has-text('Missions (')")
    # demo limit: delete synthetic measurement
    go(pg, "records"); pg.select_option("#flt select[name=astro]", index=1); pg.click("#flt button"); pg.wait_for_timeout(1200)
    shot(pg, "14a_measurements_database", full=True)
    pg.locator("tr", has_text="synthetic").first.locator("[data-edit]").click(); pg.wait_for_selector("#mef"); pg.wait_for_timeout(300)
    shot(pg, "14b_measurement_edit_form", el="#mef")
    pg.click("#mecancel"); pg.wait_for_timeout(800)
    d = pg.locator("tr", has_text="synthetic").first.locator("[data-del]"); d.click(); seen(pg); pg.locator("tr", has_text="synthetic").first.locator("[data-del]").click()
    print("  demo limit:", toast(pg)); shot(pg, "14c_demo_limit_synthetic_delete_blocked")
    go(pg, "review"); shot(pg, "15a_alert_review_admin")
    go(pg, "users"); shot(pg, "16_users_admin_demo_read_only", full=True)
    go(pg, "audit"); shot(pg, "17_audit_log")
    logout(pg); shot(pg, "02d_after_logout", el=".login-card")

    # ---------------- doctor
    login(pg, "doctor")
    shot(pg, "19a_doctor_navigation")
    go(pg, "review"); f = pg.locator("form.rv").first
    pg.locator(".alert .head").first.click(); f.locator("select").select_option("acknowledged"); f.locator("input[name=review_notes]").fill("Reviewed: re-measure at next PMC")
    seen(pg); f.locator("button").click(); print("  review:", toast(pg)); shot(pg, "15b_alert_review_doctor_saved")
    pg.evaluate("location.hash = '#users'"); pg.wait_for_timeout(700); shot(pg, "19b_doctor_users_blocked_redirect")
    logout(pg)

    # ---------------- operator
    login(pg, "operator")
    shot(pg, "19c_operator_navigation")
    go(pg, "records"); shot(pg, "19d_operator_records_no_edit_delete")
    go(pg, "profile"); shot(pg, "19e_operator_profile_read_only")
    logout(pg)

    # responsive
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    m.goto(BASE); m.wait_for_selector(".demo-acc", timeout=60000); m.wait_for_timeout(400)
    m.screenshot(path=str(OUT / "20c_login_mobile.png")); print("saved 20c_login_mobile")
    b.close()
