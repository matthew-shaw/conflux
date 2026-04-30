from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db
from config import TestConfig


@pytest.fixture
def app() -> Generator[FlaskClient, None, None]:
    """
    Create and configure a new app instance for each test.

    Returns:
        Flask: The Flask application instance.
    """
    app: Flask = create_app(TestConfig)
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.drop_all()


def test_index(app: FlaskClient) -> None:
    """
    Test the index route.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    response = app.get("/")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_accessibility(app: FlaskClient) -> None:
    """
    Test the accessibility route.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    response = app.get("/accessibility")
    assert response.status_code == 200
    assert b"<title>" in response.data


def test_cookies_get(app: FlaskClient) -> None:
    """Test the cookies route with a GET request."""
    response = app.get("/cookies")
    assert response.status_code == 200

    # Check default cookie values
    assert response.request.cookies.get("functional", "no") == "no"
    assert response.request.cookies.get("analytics", "no") == "no"


def test_http_errors(app: FlaskClient) -> None:
    """Test handling of HTTP errors."""
    response = app.get("/not-found")
    assert response.status_code == 404
    assert b"Page not found" in response.data

    response = app.get("/")
    response = app.get("/")
    response = app.get("/")
    assert response.status_code == 429
    assert b"There have been too many attempts to access this page." in response.data
