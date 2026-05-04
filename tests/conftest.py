from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db
from config import TestConfig


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    app: Flask = create_app(TestConfig)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def test_client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask):
    return app.test_cli_runner()
