from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.team import api as team_api
from app.team import ui as team_ui


def test_api_view_includes_only_active_people(app, test_client):
    """GIVEN a team with active and archived people
    WHEN the team API detail endpoint is called
    THEN the returned JSON includes only active people."""
    from datetime import datetime, timezone
    from app import db
    from app.models import Person, Role, Team

    with app.app_context():
        role = Role(name="Engineering", grade="Grade 1")
        team = Team(name="API Team")
        db.session.add_all([role, team])
        db.session.commit()

        p_active = Person(
            name="Active Person",
            email_address="active@example.com",
            location="London",
            role_id=role.id,
            team_id=team.id,
        )
        p_archived = Person(
            name="Archived Person",
            email_address="archived@example.com",
            location="London",
            role_id=role.id,
            team_id=team.id,
        )
        p_archived.archived_at = datetime.now(timezone.utc)
        db.session.add_all([p_active, p_archived])
        db.session.commit()

        assert len(team.people) == 2
        assert len(team.active_people) == 1

    # Request the API detail with people included
    response = test_client.get(f"/api/v1/teams/{team.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert "people" in data
    assert isinstance(data["people"], list)
    # Only the active person should be included
    assert any(p.get("name") == "Active Person" for p in data["people"])
    assert not any(p.get("name") == "Archived Person" for p in data["people"])
