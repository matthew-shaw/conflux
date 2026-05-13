import json
import logging
from datetime import datetime, timezone
from typing import Type

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect  # type: ignore[import]
from govuk_frontend_wtf.main import WTFormsHelpers  # type: ignore[import]
from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from app.utils.govuk_datetime import format_govuk_datetime
from config import Config


class JSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Base log structure
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        log = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "lineno": record.lineno,
        }

        # Attach any extra fields that might be present
        extras = getattr(record, "extras", None)
        if extras and isinstance(extras, dict):
            log.update(extras)

        return json.dumps(log, default=str)


def configure_structured_logging(app: "Flask") -> None:
    """Configure root logger to emit JSON structured logs to stdout."""
    level_name = app.config.get("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    # Avoid adding duplicate handlers in reload/test environments
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)


# Initialize Flask extensions. These are initialized here for easier access.
csrf: CSRFProtect = CSRFProtect()
db: SQLAlchemy = SQLAlchemy()
limiter: Limiter = Limiter(get_remote_address, default_limits=["2 per second", "60 per minute"])
migrate: Migrate = Migrate()


def create_app(config_class: Type[Config] = Config) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_class: The configuration class to use (defaults to `Config`).

    Returns:
        A configured Flask application instance.
    """
    app: Flask = Flask(__name__)  # type: ignore[assignment]
    app.config.from_object(config_class)
    # Configure structured JSON logging
    configure_structured_logging(app)
    app.jinja_env.globals["format_govuk_datetime"] = format_govuk_datetime
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True

    # Configure Jinja2 template loader to search in multiple locations.
    app.jinja_loader = ChoiceLoader(
        [
            PackageLoader("app"),  # Load templates from the 'app' package.
            PrefixLoader(
                {
                    "govuk_frontend_jinja": PackageLoader("govuk_frontend_jinja"),
                    "govuk_frontend_wtf": PackageLoader("govuk_frontend_wtf"),
                }
            ),
        ]
    )

    # Use ProxyFix middleware to handle proxies correctly.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # type: ignore[method-assign]

    # Initialize Flask extensions
    csrf.init_app(app)
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    WTFormsHelpers(app)

    # Register blueprints. These define different sections of the application.
    from app.main import bp as main_bp
    from app.person import api_bp as person_api
    from app.person import ui_bp as person_ui
    from app.role import api_bp as role_api
    from app.role import ui_bp as role_ui
    from app.search import bp as search_bp
    from app.service import api_bp as service_api
    from app.service import ui_bp as service_ui
    from app.team import api_bp as team_api
    from app.team import ui_bp as team_ui

    app.register_blueprint(main_bp)
    app.register_blueprint(person_api)
    app.register_blueprint(person_ui)
    app.register_blueprint(role_api)
    app.register_blueprint(role_ui)
    app.register_blueprint(search_bp)
    app.register_blueprint(service_api)
    app.register_blueprint(service_ui)
    app.register_blueprint(team_api)
    app.register_blueprint(team_ui)

    limiter.exempt(person_api)
    limiter.exempt(role_api)
    limiter.exempt(service_api)
    limiter.exempt(team_api)

    return app


from app import models  # noqa: E402,F401
