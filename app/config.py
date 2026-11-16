import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _db_uri():
    """SQLite file location. On Render set DATABASE_PATH (e.g. /var/data/astra_vital.db on a persistent disk)."""
    path = os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "astra_vital.db"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + path


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    # Public demo accounts (NASA Evaluator Access) shown on the login page and seeded by `flask bootstrap`.
    DEMO_ACCOUNTS_ENABLED = os.environ.get("DEMO_ACCOUNTS", "1") == "1"
    # JSON API for the GitHub Pages frontend: exact origins allowed by CORS (comma-separated, scheme+host only)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://etner249.github.io")
    API_TOKEN_HOURS = int(os.environ.get("API_TOKEN_HOURS", "8"))


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    # tests/conftest.py points SQLALCHEMY_DATABASE_URI to a temporary SQLite *file* per test
    WTF_CSRF_ENABLED = False  # CSRF is tested explicitly in tests/test_security.py
