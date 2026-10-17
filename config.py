import os
import secrets
from typing import ClassVar


def _parse_comma_separated_setting(name: str) -> list[str]:
    """Return non-blank, trimmed values from a comma-separated environment setting."""
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


class Config:
    CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL")
    CONTACT_PHONE = "02079460000"
    DEBUG = os.environ.get("DEBUG", False)
    DEPARTMENT_NAME = "Matt Shaw"
    DEPARTMENT_URL = "https://github.com/matthew-shaw"
    DOMAIN = os.environ.get("DOMAIN")
    GRADES: ClassVar[list[str]] = _parse_comma_separated_setting("GRADES")
    LOCATIONS: ClassVar[list[str]] = _parse_comma_separated_setting("LOCATIONS")
    PROFESSIONS: ClassVar[list[str]] = _parse_comma_separated_setting("PROFESSIONS")
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("VALKEY_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SERVICE_NAME = "Conflux"
    SERVICE_PHASE = "Alpha"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    VERSION = "0.13.0"


class TestConfig(Config):
    CONTACT_EMAIL = "test@example.com"
    CONTACT_PHONE = "08081570000"
    DEBUG = True
    DEPARTMENT_NAME = "Department of Magical Law Enforcement"
    DEPARTMENT_URL = "https://www.example.com/"
    RATELIMIT_HEADERS_ENABLED = True
    SECRET_KEY = secrets.token_hex(32)
    SERVICE_NAME = "Apply for a wand licence"
    SERVICE_PHASE = "Beta"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
