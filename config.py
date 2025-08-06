import os


class Config(object):
    CONTACT_EMAIL = "team@example.com"
    CONTACT_PHONE = "02079460000"
    DEPARTMENT_NAME = "Mash Software"
    DEPARTMENT_URL = "https://www.mashsoftware.com/"
    GRADES = os.environ.get("GRADES", "").split(",")
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SERVICE_NAME = "Mímir"
    SERVICE_PHASE = "Alpha"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"postgresql://{os.environ.get('POSTGRES_USER')}:"
        f"{os.environ.get('POSTGRES_PASSWORD')}@"
        f"{os.environ.get('POSTGRES_HOST')}:"
        f"{os.environ.get('POSTGRES_PORT')}/"
        f"{os.environ.get('POSTGRES_DB')}"
    )


class TestConfig(object):
    CONTACT_EMAIL = "test@example.com"
    CONTACT_PHONE = "08081570000"
    DEBUG = True
    DEPARTMENT_NAME = "Department of Magical Law Enforcement"
    DEPARTMENT_URL = "https://www.example.com/"
    RATELIMIT_HEADERS_ENABLED = True
    SECRET_KEY = "4f378500459bb58fecf903ea3c113069f11f150b33388f56fc89f7edce0e6a84"
    SERVICE_NAME = "Apply for a wand licence"
    SERVICE_PHASE = "Beta"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    TESTING = True
