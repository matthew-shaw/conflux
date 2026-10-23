from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db, limiter
from app.models import Person, Role, Team
from config import TestConfig


@pytest.fixture
def app() -> Generator[Flask]:
    app: Flask = create_app(TestConfig)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def test_client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask):
    return app.test_cli_runner()


@pytest.fixture
def _seed(app: Flask, monkeypatch: pytest.MonkeyPatch) -> tuple[UUID, UUID, UUID]:
    """Create two employee gaps for the same role and an existing person."""
    app.config.update(DOMAIN="example.com", LOCATIONS=["London"], RATELIMIT_ENABLED=False)
    monkeypatch.setattr(limiter, "enabled", False)
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        team = Team(name="Delivery")
        other_team = Team(name="Operations")
        db.session.add_all([role, team, other_team])
        db.session.flush()
        db.session.add_all(
            [
                Person(
                    name=None,
                    email_address=None,
                    location=None,
                    employment="employee",
                    role_id=role.id,
                    team_id=assignment_team.id,
                    is_gap=True,
                )
                for assignment_team in (team, other_team)
            ]
        )
        person = Person(
            name="Existing Person",
            email_address="existing@example.com",
            location="london",
            employment="employee",
            role_id=role.id,
            team_id=other_team.id,
        )
        db.session.add(person)
        db.session.commit()
        return role.id, team.id, person.id


@pytest.fixture
def gap_catalog(app: Flask, monkeypatch: pytest.MonkeyPatch) -> dict[str, UUID]:
    """Create active and archived assignments without any gaps."""
    app.config["RATELIMIT_ENABLED"] = False
    monkeypatch.setattr(limiter, "enabled", False)
    with app.app_context():
        team = Team(name="Delivery")
        role = Role(name="Engineer", grade="G7")
        other_team = Team(name="Operations")
        other_role = Role(name="Analyst", grade="G7")
        archived_team = Team(name="Retired team")
        archived_role = Role(name="Retired role", grade="G7")
        archived_team.archived_at = datetime.now(UTC)
        archived_role.archived_at = datetime.now(UTC)
        entities: dict[str, Team | Role] = {
            "team": team,
            "role": role,
            "other_team": other_team,
            "other_role": other_role,
            "archived_team": archived_team,
            "archived_role": archived_role,
        }
        db.session.add_all(entities.values())
        db.session.commit()
        return {key: entity.id for key, entity in entities.items()}
