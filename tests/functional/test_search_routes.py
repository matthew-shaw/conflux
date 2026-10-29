import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Person, Role, Service, Team
from app.search import routes as search_routes


def test_search_results_link_to_each_entity_in_name_order(app: Flask, test_client: FlaskClient) -> None:
    """
    GIVEN matching roles, people, teams, and services
    WHEN the search page is queried
    THEN results are ordered by name and link to each entity's detail page.
    """
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        role = Role(name="Platform Engineer", grade="Grade 7")
        team = Team(name="Platform Team")
        db.session.add_all([role, team])
        db.session.flush()

        person = Person(
            name="Alice Example",
            email_address="alice@example.com",
            location="Platform",
            employment="employee",
            role_id=role.id,
            team_id=team.id,
        )
        service = Service(name="Platform Service", description="Platform service", team_id=team.id)
        db.session.add_all([person, service])
        db.session.commit()

        role_id = str(role.id)
        person_id = str(person.id)
        team_id = str(team.id)
        service_id = str(service.id)

    response = test_client.get("/search/?q=Platform")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert body.index("Alice Example") < body.index("Platform Engineer")
    assert body.index("Platform Engineer") < body.index("Platform Service")
    assert body.index("Platform Service") < body.index("Platform Team")
    assert f'href="/people/{person_id}"' in body
    assert f'href="/roles/{role_id}"' in body
    assert f'href="/services/{service_id}"' in body
    assert f'href="/teams/{team_id}"' in body


def test_search_matches_role_grade_and_person_location(app: Flask, test_client: FlaskClient) -> None:
    """
    GIVEN a role whose grade and a person's location match the query
    WHEN the search page is queried
    THEN both supported non-name fields produce results.
    """
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        role = Role(name="Engineer", grade="Platform Grade")
        db.session.add(role)
        db.session.flush()
        person = Person(
            name="Alice Example",
            email_address="alice@example.com",
            location="Platform",
            employment="employee",
            role_id=role.id,
        )
        db.session.add(person)
        db.session.commit()

    response = test_client.get("/search/?q=Platform")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Engineer" in body
    assert "Alice Example" in body


def test_search_without_query_does_not_call_search_service(
    app: Flask,
    test_client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    GIVEN a search page opened without a query
    WHEN the page is requested
    THEN the search service is not called and no empty-state message is shown.
    """
    app.config["RATELIMIT_ENABLED"] = False
    monkeypatch.setattr(
        search_routes,
        "search_entries",
        lambda query: pytest.fail("Search service was called"),
    )

    response = test_client.get("/search/")

    assert response.status_code == 200
    assert b"No results" not in response.data


def test_search_shows_empty_state_when_there_are_no_matches(app: Flask, test_client: FlaskClient) -> None:
    """
    GIVEN a query with no matching entities
    WHEN the search page is requested
    THEN the page displays the no-results message.
    """
    app.config["RATELIMIT_ENABLED"] = False

    response = test_client.get("/search/?q=NoMatchingEntity")

    assert response.status_code == 200
    assert b"No results" in response.data


def test_search_returns_service_unavailable_on_database_error(
    app: Flask,
    test_client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    GIVEN the search service raises a database error
    WHEN a search query is submitted
    THEN the route returns the service-unavailable response.
    """
    app.config["RATELIMIT_ENABLED"] = False

    def raise_database_error(query: str) -> list[dict[str, object]]:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(search_routes, "search_entries", raise_database_error)

    response = test_client.get("/search/?q=Platform")

    assert response.status_code == 503
    assert b"Service temporarily unavailable" in response.data
