"""ASTRA VITAL — Academic Edition (Python Flask + SQLite).
Adaptation of the ASTRA VITAL project submitted by team NYXARA NOVA to the NASA Space Apps Challenge 2026.
The NASA submission was the static web edition (https://github.com/Etner249/astra-vital); this Flask edition is a
university adaptation. Educational prototype — not a medical device.
"""
import os
import click
from flask import Flask, render_template, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from .extensions import db, login_manager, csrf
from .config import Config, ProductionConfig


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")   # SQLite enforces FOREIGN KEY constraints only when enabled
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def create_app(config_object=None, **overrides):
    app = Flask(__name__)
    if config_object is None:
        config_object = ProductionConfig if os.environ.get("FLASK_ENV_MODE") == "production" else Config
    app.config.from_object(config_object)
    app.config.update(overrides)
    if app.config.get("SECRET_KEY") == "dev-only-change-me" and os.environ.get("FLASK_ENV_MODE") == "production":
        raise RuntimeError("SECRET_KEY must be set in production")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .models import User  # noqa

    @login_manager.user_loader
    def load_user(uid):
        u = db.session.get(User, int(uid))
        return u if u and u.is_active_account else None

    from . import auth, main, crud
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(crud.bp)
    from . import api
    app.register_blueprint(api.bp)

    from .decorators import can, PERMISSIONS
    from .models import ROLE_LABELS
    app.jinja_env.globals.update(can=can, ROLE_LABELS=ROLE_LABELS, PERMS=PERMISSIONS)
    from .demo import mask_email as _mask, is_demo_user as _isdemo
    app.jinja_env.filters["mask_email"] = _mask
    app.jinja_env.globals["is_demo_user"] = _isdemo

    def _other(m):
        parts = [("Sleep", m.sleep_hours, "h"), ("Exercise", m.exercise_min, "min"), ("Fatigue", m.fatigue, "/7"),
                 ("Mood", m.mood, "/5"), ("Glucose", m.glucose, "mg/dL")]
        return " · ".join(f"{k} {v}{u if u.startswith('/') else ' ' + u}" for k, v, u in parts if v is not None) or "—"
    app.jinja_env.filters["other_indicators"] = _other

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        return resp

    for code, title in ((400, "Bad request"), (403, "Access denied"), (404, "Not found"), (405, "Method not allowed"), (500, "Server error")):
        def handler(e, code=code, title=title):
            if code == 500:
                db.session.rollback()
            if request.path.startswith("/api/"):
                return {"error": title, "status": code}, code
            desc = getattr(e, "description", None)
            custom = desc if code == 403 and desc and not desc.startswith("You don't have the permission") else None
            return render_template("errors/error.html", code=code, title=title, message=custom), code
        app.register_error_handler(code, handler)

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template("errors/error.html", code=400, title="Form expired or invalid (CSRF check failed). Reload the page and try again."), 400

    register_cli(app)
    return app


def register_cli(app):
    from .models import User, Astronaut
    from .demo import ensure_demo_accounts
    from .seed import seed_demo

    @app.cli.command("init-db")
    def init_db():
        """Create all SQLite tables (idempotent)."""
        db.create_all()
        click.echo(f"Database ready: {app.config['SQLALCHEMY_DATABASE_URI']}")

    @app.cli.command("create-user")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Full name")
    @click.option("--role", type=click.Choice(["admin", "doctor", "operator"]), default="admin")
    @click.password_option()
    def create_user(email, name, role, password):
        """Create a user interactively (password is prompted, never stored in plain text)."""
        db.create_all()
        if User.query.filter_by(email=email.lower()).first():
            raise click.ClickException("User already exists")
        u = User(email=email.lower(), full_name=name, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo(f"Created {role} {email}")

    @app.cli.command("seed-demo")
    def seed():
        """Insert SYNTHETIC demo missions, astronauts and measurements (flagged is_synthetic)."""
        db.create_all()
        click.echo(f"Inserted {seed_demo()} synthetic measurements")

    @app.cli.command("bootstrap")
    def bootstrap():
        """Deployment start-up: create tables, create users from environment variables if missing, seed demo data."""
        db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "", 1)
        if os.path.exists(db_path):
            click.echo(f"Existing SQLite database found at {db_path} ({os.path.getsize(db_path)} bytes)")
        else:
            click.echo(f"No SQLite database at {db_path}: creating a new one")
        db.create_all()
        click.echo(f"Database contents: {User.query.count()} users, {Astronaut.query.count()} astronauts")
        for role in ("ADMIN", "DOCTOR", "OPERATOR"):
            email, pwd = os.environ.get(f"{role}_EMAIL"), os.environ.get(f"{role}_PASSWORD")
            if email and pwd and not User.query.filter_by(email=email.lower()).first():
                u = User(email=email.lower(), full_name=f"Demo {role.title()}", role=role.lower())
                u.set_password(pwd)
                db.session.add(u)
                click.echo(f"Created {role.lower()} {email}")
        db.session.commit()
        if os.environ.get("SEED_DEMO", "1") == "1":
            click.echo(f"Seeded {seed_demo()} synthetic measurements")
        if app.config["DEMO_ACCOUNTS_ENABLED"]:
            created, repaired = ensure_demo_accounts()
            click.echo(f"Demo accounts ready: {created} created, {repaired} repaired, {User.query.filter_by(is_demo=True).count()} total")

    @app.cli.command("seed-demo-accounts")
    def seed_demo_accounts():
        """Create (or repair) the three public demo accounts. Idempotent: never creates duplicates."""
        db.create_all()
        created, repaired = ensure_demo_accounts()
        click.echo(f"Demo accounts ready: {created} created, {repaired} repaired")
