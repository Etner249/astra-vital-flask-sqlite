"""Captures REAL screenshots of the running Flask app (local server) for the academic evidence folder.
Usage: start the app, then  python3 scripts/capture_evidence.py http://127.0.0.1:5055
Credentials are read from environment variables (ADMIN_EMAIL/ADMIN_PASSWORD, DOCTOR_*, OPERATOR_*); never hard-coded."""
import os, sys, pathlib
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip('/')
OUT = pathlib.Path(__file__).resolve().parent.parent / 'docs/academic/evidence'
OUT.mkdir(parents=True, exist_ok=True)

def shot(pg, name, full=False):
    pg.wait_for_timeout(350); pg.screenshot(path=str(OUT / f'{name}.png'), full_page=full); print('saved', name)

def login(pg, role):
    pg.goto(BASE + '/login'); pg.fill('#email', os.environ[f'{role}_EMAIL']); pg.fill('#password', os.environ[f'{role}_PASSWORD']); pg.click('#submit'); pg.wait_for_load_state()

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}); pg = ctx.new_page()
    pg.goto(BASE + '/login'); shot(pg, '01_login')
    login(pg, 'ADMIN'); shot(pg, '02_dashboard_admin', True)
    pg.goto(BASE + '/astronauts'); shot(pg, '03_astronauts_list')
    pg.goto(BASE + '/astronauts/new'); pg.fill('#code', 'AV-CREW-05'); pg.fill('#full_name', 'Evidence Crew Member Echo (fictional)')
    pg.fill('#demo_age', '38'); pg.fill('#role_on_board', 'Payload Specialist'); pg.select_option('#mission_id', index=1); shot(pg, '04a_astronaut_create_form')
    pg.click('#submit'); pg.wait_for_load_state(); shot(pg, '04b_astronaut_created')
    aid = pg.url.rstrip('/').split('/')[-1]
    pg.goto(f'{BASE}/astronauts/{aid}/edit'); pg.fill('#role_on_board', 'Payload Specialist & Medical Backup'); pg.select_option('#status', 'active'); shot(pg, '05a_astronaut_edit_form')
    pg.click('#submit'); pg.wait_for_load_state(); shot(pg, '05b_astronaut_updated')
    pg.goto(f'{BASE}/measurements/new?astronaut_id={aid}')
    pg.fill('#heart_rate', '112'); pg.fill('#systolic_bp', '128'); pg.fill('#diastolic_bp', '82'); pg.fill('#spo2', '94'); pg.fill('#temperature', '37.1'); pg.fill('#respiratory_rate', '22')
    pg.fill('#notes', 'Recorded after EVA simulation (evidence capture)'); shot(pg, '08a_measurement_create_form')
    pg.click('#submit'); pg.wait_for_load_state(); shot(pg, '08b_measurement_saved_with_alerts', True)
    pg.goto(BASE + '/measurements'); shot(pg, '07_measurements_management')
    pg.goto(BASE + '/measurements?astronaut_id=1'); shot(pg, '09_measurement_history_filtered')
    pg.goto(BASE + '/alerts'); shot(pg, '10a_alerts')
    pg.click('.alert.priority a'); pg.wait_for_load_state(); shot(pg, '10b_alert_detail_review', True)
    pg.goto(f'{BASE}/astronauts/{aid}/delete'); shot(pg, '06a_astronaut_delete_confirm')
    if pg.locator('input[name=confirm_open_alerts]').count(): pg.check('input[name=confirm_open_alerts]')
    pg.click('button.danger'); pg.wait_for_load_state(); shot(pg, '06b_astronaut_deleted')
    pg.goto(BASE + '/users'); shot(pg, '11_users_and_permissions', True)
    pg.goto(BASE + '/missions'); shot(pg, '16_missions')
    pg.goto(BASE + '/reports'); shot(pg, '17_reports')
    pg.goto(BASE + '/risks'); shot(pg, '18_risk_center')
    pg.goto(BASE + '/nasa-data'); shot(pg, '19_nasa_data')
    pg.goto(BASE + '/audit'); shot(pg, '20_audit_log')
    ctx.close()
    for role in ('DOCTOR', 'OPERATOR'):
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}); pg = ctx.new_page(); login(pg, role)
        shot(pg, f'12_{role.lower()}_dashboard')
        pg.goto(BASE + '/users'); shot(pg, f'12_{role.lower()}_users_forbidden_403')
        ctx.close()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2); pg = ctx.new_page(); login(pg, 'ADMIN'); shot(pg, '21_mobile_dashboard')
    b.close()
