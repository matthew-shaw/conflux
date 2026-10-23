"""Functional coverage for adding, viewing, editing and removing gaps through people routes."""

from uuid import UUID, uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import db
from app.models import Person
from app.person.service import create_gap, create_person, get_gap


def _gap_count() -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(Person).where(Person.is_gap.is_(True))) or 0


@pytest.fixture
def gap_id(app: Flask, gap_catalog: dict[str, UUID]) -> UUID:
    """Create one employee gap for the catalogue team and role."""
    with app.app_context():
        return create_gap("employee", gap_catalog["role"], gap_catalog["team"]).id


@pytest.mark.parametrize("with_team", [True, False])
def test_add_gap_from_people_list(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], with_team: bool
) -> None:
    """
    GIVEN the people list and the add gap form
    WHEN a gap is submitted with an employment type, role and optional team
    THEN the gap is created and the user is returned to the people list with a message
    """
    assert 'href="/people/gaps/new"' in test_client.get("/people/").get_data(as_text=True)
    form = test_client.get("/people/gaps/new").get_data(as_text=True)
    assert 'name="employment"' in form and 'name="role"' in form and 'name="team"' in form
    assert 'name="location"' not in form and 'name="name"' not in form

    team = str(gap_catalog["team"]) if with_team else ""
    response = test_client.post(
        "/people/gaps/new",
        data={"employment": "contractor", "role": str(gap_catalog["role"]), "team": team},
        follow_redirects=True,
    )
    assert response.request.path == "/people/"
    assert "Gap</a> has been created" in response.get_data(as_text=True)
    with app.app_context():
        gap = db.session.execute(db.select(Person).where(Person.is_gap.is_(True))).scalar_one()
        assert (gap.employment, gap.role_id) == ("contractor", gap_catalog["role"])
        assert gap.team_id == (gap_catalog["team"] if with_team else None)
        assert gap.location is None


def test_team_page_links_to_prefilled_gap_form(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID]
) -> None:
    """
    GIVEN an active team
    WHEN its page and its add gap link are opened
    THEN the gap form has the team preselected
    """
    team_id = gap_catalog["team"]
    page = test_client.get(f"/teams/{team_id}").get_data(as_text=True)
    assert f'href="/people/gaps/new?team={team_id}"' in page
    form = test_client.get(f"/people/gaps/new?team={team_id}").get_data(as_text=True)
    assert f'<option selected value="{team_id}">' in form or f'value="{team_id}" selected' in form


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"employment": "employee", "role": "", "team": ""}, "Select a role"),
        ({"employment": "", "role": "ROLE", "team": ""}, "Select an employment type"),
    ],
)
def test_gap_form_requires_employment_and_role(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], data: dict[str, str], message: str
) -> None:
    """
    GIVEN the add gap form
    WHEN it is submitted without a role or employment type
    THEN an error is shown and no gap is created
    """
    data = {key: str(gap_catalog["role"]) if value == "ROLE" else value for key, value in data.items()}
    response = test_client.post("/people/gaps/new", data=data)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    with app.app_context():
        assert _gap_count() == 0


@pytest.mark.parametrize("choice", ["archived_team", "archived_role"])
def test_gap_form_rejects_archived_choices(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], choice: str
) -> None:
    """
    GIVEN an archived team or role
    WHEN it is submitted on the add gap form
    THEN it is rejected as an invalid choice and no gap is created
    """
    data = {"employment": "employee", "role": str(gap_catalog["role"]), "team": str(gap_catalog["team"])}
    data["team" if choice == "archived_team" else "role"] = str(gap_catalog[choice])
    response = test_client.post("/people/gaps/new", data=data)
    assert response.status_code == 200
    assert "Not a valid choice" in response.get_data(as_text=True)
    with app.app_context():
        assert _gap_count() == 0


def test_gaps_appear_in_people_list_team_and_api(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], gap_id: UUID
) -> None:
    """
    GIVEN a gap and a real person
    WHEN the people list, team page and people API are requested
    THEN the gap is shown marked as a gap and can be filtered
    """
    with app.app_context():
        person_id = create_person(
            "Real Person", "real@example.com", "london", "employee", gap_catalog["role"], None, None
        ).id
    body = test_client.get("/people/").get_data(as_text=True)
    assert '<strong class="govuk-tag govuk-tag--yellow">' in body
    assert f'href="/people/{gap_id}" class="govuk-link govuk-!-font-weight-bold">Gap</a>' in body
    assert "—" in body
    assert f'href="/people/{gap_id}"' not in test_client.get("/people/?kind=people").get_data(as_text=True)
    assert "Real Person" not in test_client.get("/people/?kind=gaps").get_data(as_text=True)

    team_page = test_client.get(f"/teams/{gap_catalog['team']}").get_data(as_text=True)
    assert "0 people, 1 open gap" in team_page
    assert f'href="/people/{gap_id}" class="govuk-link govuk-!-font-weight-bold">Gap</a>' in team_page

    api = test_client.get("/api/v1/people/").get_json()
    assert {(item["id"], item["is_gap"]) for item in api} == {(str(gap_id), True), (str(person_id), False)}
    assert [item["id"] for item in test_client.get("/api/v1/people/?is_gap=true").get_json()] == [str(gap_id)]
    assert [item["id"] for item in test_client.get("/api/v1/people/?is_gap=false").get_json()] == [str(person_id)]
    detail = test_client.get(f"/api/v1/people/{gap_id}").get_json()
    assert detail["is_gap"] is True
    assert (detail["name"], detail["location"], detail["email_address"]) == (None, None, None)
    assert detail["role"]["id"] == str(gap_catalog["role"])
    team_api = test_client.get(f"/api/v1/teams/{gap_catalog['team']}").get_json()
    assert [item["id"] for item in team_api["people"]] == [str(gap_id)]


def test_gap_view_offers_remove_not_archive(test_client: FlaskClient, gap_id: UUID) -> None:
    """
    GIVEN a gap
    WHEN its view and edit pages are requested
    THEN both offer removing the gap and neither offers archiving
    """
    for path in (f"/people/{gap_id}", f"/people/{gap_id}/edit"):
        body = test_client.get(path).get_data(as_text=True)
        assert f'href="/people/{gap_id}/delete-gap"' in body
        assert "Remove gap" in body
        assert f"/people/{gap_id}/archive" not in body
        assert "Archive" not in body


def test_edit_gap_form_only_shows_assignment_fields(test_client: FlaskClient, gap_id: UUID) -> None:
    """
    GIVEN a gap
    WHEN its edit page is requested
    THEN only employment type, role and team are shown, prefilled with its values
    """
    body = test_client.get(f"/people/{gap_id}/edit").get_data(as_text=True)
    assert 'name="employment"' in body and 'name="role"' in body and 'name="team"' in body
    for field in ("name", "email_address", "location", "manager", "fill_gap", "leave_gap"):
        assert f'name="{field}"' not in body
    assert "Edit gap" in body


def test_edit_gap_updates_assignment_and_ignores_personal_fields(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], gap_id: UUID
) -> None:
    """
    GIVEN a gap
    WHEN it is edited with a new employment type, role, no team and extra personal fields
    THEN only the assignment changes and it remains a gap
    """
    response = test_client.post(
        f"/people/{gap_id}/edit",
        data={
            "employment": "contractor",
            "role": str(gap_catalog["other_role"]),
            "team": "",
            "name": "Sneaky Name",
            "location": "london",
            "email_address": "sneaky@example.com",
        },
        follow_redirects=True,
    )
    assert response.request.path == "/people/"
    assert "Gap</a> has been updated" in response.get_data(as_text=True)
    with app.app_context():
        gap = get_gap(gap_id)
        assert (gap.employment, gap.role_id, gap.team_id) == ("contractor", gap_catalog["other_role"], None)
        assert (gap.is_gap, gap.name, gap.location, gap.email_address) == (True, None, None, None)


@pytest.mark.parametrize("missing", ["role", "employment"])
def test_edit_gap_requires_role_and_employment(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], gap_id: UUID, missing: str
) -> None:
    """
    GIVEN a gap
    WHEN it is edited with its role or employment type cleared
    THEN an error is shown and the gap is unchanged
    """
    data = {"employment": "contractor", "role": str(gap_catalog["other_role"]), "team": ""}
    data[missing] = ""
    response = test_client.post(f"/people/{gap_id}/edit", data=data)
    assert response.status_code == 200
    assert "There is a problem" in response.get_data(as_text=True)
    with app.app_context():
        gap = get_gap(gap_id)
        assert (gap.employment, gap.role_id, gap.team_id) == ("employee", gap_catalog["role"], gap_catalog["team"])


def test_remove_gap_requires_confirmation(app: Flask, test_client: FlaskClient, gap_id: UUID) -> None:
    """
    GIVEN a gap
    WHEN the removal page is submitted without and then with confirmation
    THEN the gap is kept until confirmed, then deleted with a message on the people list
    """
    page = test_client.get(f"/people/{gap_id}/delete-gap").get_data(as_text=True)
    assert "This cannot be undone" in page
    assert f'href="/people/{gap_id}"' in page

    response = test_client.post(f"/people/{gap_id}/delete-gap", data={})
    assert response.status_code == 200
    with app.app_context():
        assert _gap_count() == 1

    response = test_client.post(f"/people/{gap_id}/delete-gap", data={"confirm": "y"}, follow_redirects=True)
    assert response.request.path == "/people/"
    assert "Gap has been removed" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Person, gap_id) is None


def test_gaps_cannot_be_archived_or_restored(
    app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID], gap_id: UUID
) -> None:
    """
    GIVEN a gap and a real person
    WHEN the gap's archive and restore pages are requested, or a real person's removal page
    THEN each returns 404 and the archived list does not show the gap
    """
    with app.app_context():
        person_id = create_person(
            "Real Person", "real@example.com", "london", "employee", gap_catalog["role"], None, None
        ).id
    for path in (f"/people/{gap_id}/archive", f"/people/{gap_id}/restore"):
        assert test_client.get(path).status_code == 404
        assert test_client.post(path, data={"confirm": "y"}).status_code == 404
    assert test_client.get(f"/people/{person_id}/delete-gap").status_code == 404
    assert test_client.get(f"/people/{uuid4()}/delete-gap").status_code == 404
    assert "Vacancy" not in test_client.get("/people/?status=archived").get_data(as_text=True)
    with app.app_context():
        assert get_gap(gap_id).archived_at is None


def test_standalone_gap_pages_are_removed(test_client: FlaskClient) -> None:
    """
    GIVEN the application
    WHEN the old gaps pages and API are requested and the menu is rendered
    THEN they are not found and there is no Gaps menu item
    """
    assert test_client.get("/gaps/").status_code == 404
    assert test_client.get("/api/v1/gaps/").status_code == 404
    assert 'href="/gaps/"' not in test_client.get("/people/").get_data(as_text=True)


@pytest.mark.parametrize("keyword", ["dElIvErY", "eNgInEeR"])
def test_search_finds_gaps_by_team_or_role(
    test_client: FlaskClient, gap_id: UUID, gap_catalog: dict[str, UUID], keyword: str
) -> None:
    """
    GIVEN a gap in a team for a role
    WHEN global search matches the team or role name
    THEN the gap is listed and links to its view page
    """
    body = test_client.get("/search/", query_string={"q": keyword}).get_data(as_text=True)
    assert f'href="/people/{gap_id}" class="govuk-link">Gap (Delivery)</a>' in body
