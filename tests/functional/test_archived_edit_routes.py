from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.person import ui as person_ui
from app.role import ui as role_ui
from app.service import ui as service_ui
from app.team import ui as team_ui


@pytest.mark.parametrize(
    ("ui", "route", "getter", "message"),
    [
        (role_ui, "roles", "get_role", "This role cannot be changed because it has been archived."),
        (person_ui, "people", "get_person", "This person cannot be changed because they have been archived."),
        (team_ui, "teams", "get_team", "This team cannot be changed because it has been archived."),
        (service_ui, "services", "get_service", "This service cannot be changed because it has been archived."),
    ],
)
@pytest.mark.parametrize("method", ["get", "post"])
def test_archived_entity_edit_redirects_to_detail(ui, route, getter, message, method, monkeypatch, test_client):
    entity_id = UUID("00000000-0000-0000-0000-000000000001")
    entity = SimpleNamespace(id=entity_id, archived_at=datetime.now(UTC))
    monkeypatch.setattr(ui, getter, lambda id, *args, **kwargs: entity)

    response = getattr(test_client, method)(f"/{route}/{entity_id}/edit", data={} if method == "post" else None)

    assert response.status_code == 302
    assert response.headers["Location"] == f"/{route}/{entity_id}"
    with test_client.session_transaction() as session:
        assert session["_flashes"] == [("message", message)]


@pytest.mark.parametrize(
    ("ui", "route", "getter", "make_entity"),
    [
        (
            role_ui,
            "roles",
            "get_role",
            lambda id, archived_at, updated_at: SimpleNamespace(
                id=id,
                name="Archived role",
                grade="Grade 1",
                profession=None,
                archived_at=archived_at,
                updated_at=updated_at,
                active_people=[],
                gaps=[],
            ),
        ),
        (
            person_ui,
            "people",
            "get_person",
            lambda id, archived_at, updated_at: SimpleNamespace(
                id=id,
                name="Archived person",
                email_address="archived@example.test",
                role=SimpleNamespace(id=id, name="Role"),
                team=None,
                manager=None,
                location="London",
                employment="employee",
                archived_at=archived_at,
                updated_at=updated_at,
                reports=[],
            ),
        ),
        (
            team_ui,
            "teams",
            "get_team",
            lambda id, archived_at, updated_at: SimpleNamespace(
                id=id,
                name="Archived team",
                archived_at=archived_at,
                updated_at=updated_at,
                active_people=[],
                services=[],
            ),
        ),
        (
            service_ui,
            "services",
            "get_service",
            lambda id, archived_at, updated_at: SimpleNamespace(
                id=id,
                name="Archived service",
                description=None,
                team=None,
                archived_at=archived_at,
                updated_at=updated_at,
            ),
        ),
    ],
)
@pytest.mark.parametrize("archived", [True, False])
def test_detail_page_only_offers_edit_actions_for_active_entities(
    ui, route, getter, make_entity, archived, monkeypatch, test_client
):
    entity_id = UUID("00000000-0000-0000-0000-000000000001")
    timestamp = datetime.now(UTC)
    entity = make_entity(entity_id, timestamp if archived else None, timestamp)
    monkeypatch.setattr(ui, getter, lambda id, *args, **kwargs: entity)

    response = test_client.get(f"/{route}/{entity_id}")

    assert response.status_code == 200
    edit_link = f"/{route}/{entity_id}/edit"
    assert (edit_link in response.get_data(as_text=True)) is not archived
