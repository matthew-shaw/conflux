import os


class Config(object):
    CONTACT_EMAIL = "team@example.com"
    CONTACT_PHONE = "02079460000"
    DEPARTMENT_NAME = "Mash Software"
    DEPARTMENT_URL = "https://www.mashsoftware.com/"
    GRADES = os.environ.get("GRADES", "").split(",")
    LOCATIONS = [loc.strip() for loc in os.environ.get("LOCATIONS", "").split(",")]
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("VALKEY_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SERVICE_NAME = "Conflux"
    SERVICE_PHASE = "Alpha"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class TestConfig(Config):
    CONTACT_EMAIL = "test@example.com"
    CONTACT_PHONE = "08081570000"
    DEBUG = True
    DEPARTMENT_NAME = "Department of Magical Law Enforcement"
    DEPARTMENT_URL = "https://www.example.com/"
    RATELIMIT_HEADERS_ENABLED = True
    SECRET_KEY = "4f378500459bb58fecf903ea3c113069f11f150b33388f56fc89f7edce0e6a84"  # nosec B105
    SERVICE_NAME = "Apply for a wand licence"
    SERVICE_PHASE = "Beta"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
