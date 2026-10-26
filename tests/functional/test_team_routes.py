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


def test_create_team_saves_configured_type(app, test_client) -> None:
    """
    GIVEN team types configured for the application
    WHEN a team is created with one of those types
    THEN the selected type is persisted and included in the team API.
    """
    from app import db
    from app.models import Team

    app.config["TEAM_TYPES"] = ["Stream-aligned", "Enabling"]
    response = test_client.post(
        "/teams/new",
        data={"name": "Product Team", "type": "Stream-aligned"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        team = db.session.execute(db.select(Team).filter_by(name="Product Team")).scalar_one()
        assert team.type == "Stream-aligned"
        response = test_client.get(f"/api/v1/teams/{team.id}")
        assert response.get_json()["type"] == "Stream-aligned"


def test_edit_team_updates_type(app, test_client) -> None:
    """
    GIVEN an existing team and configured team types
    WHEN its type is changed through the edit form
    THEN the updated type is persisted.
    """
    from app import db
    from app.models import Team

    app.config["TEAM_TYPES"] = ["Stream-aligned", "Platform"]
    with app.app_context():
        team = Team(name="Product Team", type="Stream-aligned")
        db.session.add(team)
        db.session.commit()
        team_id = team.id

    response = test_client.post(
        f"/teams/{team_id}/edit",
        data={"name": "Product Team", "type": "Platform"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        updated_team = db.session.get(Team, team_id)
        assert updated_team is not None
        assert updated_team.type == "Platform"


def test_team_type_filter_and_sort(app, test_client) -> None:
    """
    GIVEN teams with different configured types
    WHEN the teams API is filtered and sorted by team type
    THEN only matching teams are returned in type order.
    """
    from app import db
    from app.models import Team

    with app.app_context():
        db.session.add_all(
            [
                Team(name="Zulu Team", type="Enabling"),
                Team(name="Alpha Team", type="Stream-aligned"),
                Team(name="Bravo Team", type="Enabling"),
            ]
        )
        db.session.commit()

    filtered = test_client.get("/api/v1/teams/?type=Enabling")
    assert filtered.status_code == 200
    assert [team["name"] for team in filtered.get_json()] == ["Bravo Team", "Zulu Team"]

    sorted_teams = test_client.get("/api/v1/teams/?sort=type")
    assert sorted_teams.status_code == 200
    assert [(team["type"], team["name"]) for team in sorted_teams.get_json()] == [
        ("Enabling", "Bravo Team"),
        ("Enabling", "Zulu Team"),
        ("Stream-aligned", "Alpha Team"),
    ]


def test_unset_team_type_uses_red_none_tag(app, test_client) -> None:
    """
    GIVEN a team without a selected type
    WHEN the team list and detail pages are viewed
    THEN the type is displayed as a red GOV.UK tag labelled None.
    """
    from app import db
    from app.models import Team

    with app.app_context():
        team = Team(name="Uncategorised Team")
        db.session.add(team)
        db.session.commit()
        team_id = team.id

    list_response = test_client.get("/teams/")
    detail_response = test_client.get(f"/teams/{team_id}")
    list_html = " ".join(list_response.get_data(as_text=True).split())
    detail_html = " ".join(detail_response.get_data(as_text=True).split())
    expected_tag = '<strong class="govuk-tag govuk-tag--red"> None </strong>'

    assert list_response.status_code == 200
    assert expected_tag in list_html
    assert detail_response.status_code == 200
    assert expected_tag in detail_html
