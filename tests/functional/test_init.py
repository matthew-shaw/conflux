from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app
from config import TestConfig


def test_create_app() -> None:
    """Verify that create_app returns a configured Flask app instance."""
    app: Flask = create_app(TestConfig)
    assert isinstance(app, Flask)


def test_config_loaded_with_context(app: Flask) -> None:
    """Verify config is loaded correctly within an app context."""
    with app.app_context():
        assert app.config["DEBUG"] == TestConfig.DEBUG


def test_config_loaded(app: Flask) -> None:
    """Verify config is loaded correctly (outside app context)."""
    assert app.config["DEBUG"] == TestConfig.DEBUG


def test_jinja_env_config(app: Flask) -> None:
    """Verify Jinja environment configuration."""
    assert app.jinja_env.lstrip_blocks is True
    assert app.jinja_env.trim_blocks is True


def test_middleware_applied(app: Flask) -> None:
    """Verify that the ProxyFix middleware is applied to the app."""
    assert isinstance(app.wsgi_app, ProxyFix)


def test_extensions_initialized(app: Flask) -> None:
    """Verify that core Flask extensions are initialized."""
    assert "csrf" in app.extensions
    assert "limiter" in app.extensions


def test_blueprints_registered(app: Flask) -> None:
    """Verify that blueprints are registered with the app."""
    assert "main" in app.blueprints
