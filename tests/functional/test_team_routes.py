from datetime import UTC


def test_api_view_includes_only_active_people(app, test_client):
    """GIVEN a team with active and archived people
    WHEN the team API detail endpoint is called
    THEN the returned JSON includes only active people."""
    from datetime import datetime

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
            employment="employee",
            role_id=role.id,
            team_id=team.id,
        )
        p_archived = Person(
            name="Archived Person",
            email_address="archived@example.com",
            location="London",
            employment="employee",
            role_id=role.id,
            team_id=team.id,
        )
        p_archived.archived_at = datetime.now(UTC)
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


def test_team_list_includes_gap_count(app, test_client):
    """
    GIVEN a team with two open gaps
    WHEN the team list page is viewed
    THEN the page shows a Gaps column with the team's gap count
    """
    from app import db
    from app.models import Person, Role, Team

    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        team = Team(name="Team with gaps")
        role = Role(name="Engineer", grade="Grade 7")
        second_role = Role(name="Designer", grade="Grade 6")
        db.session.add_all([team, role, second_role])
        db.session.flush()
        db.session.add_all(
            [
                Person(
                    name=None,
                    email_address=None,
                    location=None,
                    employment="employee",
                    role_id=role.id,
                    team_id=team.id,
                    is_gap=True,
                ),
                Person(
                    name=None,
                    email_address=None,
                    location=None,
                    employment="employee",
                    role_id=second_role.id,
                    team_id=team.id,
                    is_gap=True,
                ),
            ]
        )
        db.session.commit()

    response = test_client.get("/teams/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Gaps" in body
    assert "Team with gaps" in body
    assert '<td class="govuk-table__cell">2</td>' in body
