from app import db
from app.models import Role


def test_role_profession_create_edit_and_display(app, test_client):
    """
    GIVEN configured profession choices
    WHEN a role is created, viewed, edited and cleared
    THEN each role page displays the selected value or None.
    """
    app.config["GRADES"] = ["Grade 7"]
    app.config["PROFESSIONS"] = ["Engineering"]
    app.config["RATELIMIT_ENABLED"] = False

    response = test_client.post(
        "/roles/new",
        data={
            "name": "Software Engineer",
            "grade": "Grade 7",
            "profession": "Engineering",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        role = db.session.scalar(db.select(Role).where(Role.name == "Software Engineer"))
        assert role is not None
        role_id = role.id

    response = test_client.get(f"/roles/{role_id}")
    assert response.status_code == 200
    assert b"Engineering" in response.data

    response = test_client.post(
        f"/roles/{role_id}/edit",
        data={"name": "Software Engineer", "grade": "Grade 7", "profession": ""},
    )
    assert response.status_code == 302

    with app.app_context():
        role = db.session.get(Role, role_id)
        assert role is not None
        assert role.profession is None

    response = test_client.get(f"/roles/{role_id}")
    assert response.status_code == 200
    assert b"None" in response.data


def test_role_profession_edit_preserves_removed_choice(app, test_client):
    """
    GIVEN a saved profession removed from config
    WHEN the role is edited
    THEN its value is retained."""
    app.config["GRADES"] = ["Grade 7"]
    app.config["PROFESSIONS"] = ["Engineering"]
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        role = Role(name="Software Engineer", grade="Grade 7", profession="Legal")
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    response = test_client.get(f"/roles/{role_id}/edit")

    assert response.status_code == 200
    assert b'value="Legal"' in response.data
    assert b"Legal" in response.data


def test_role_profession_create_rejects_unconfigured_value(app, test_client):
    """
    GIVEN a configured list of professions
    WHEN a forged profession is submitted while creating a role
    THEN the role is not created and the form is redisplayed.
    """
    app.config["GRADES"] = ["Grade 7"]
    app.config["PROFESSIONS"] = ["Engineering"]
    app.config["RATELIMIT_ENABLED"] = False

    response = test_client.post(
        "/roles/new",
        data={"name": "Software Engineer", "grade": "Grade 7", "profession": "Legal"},
    )

    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(Role).where(Role.name == "Software Engineer")) is None


def test_role_profession_edit_rejects_unconfigured_value(app, test_client):
    """
    GIVEN a role with a removed profession
    WHEN a different unconfigured profession is submitted while editing
    THEN the saved profession is unchanged and the form is redisplayed.
    """
    app.config["GRADES"] = ["Grade 7"]
    app.config["PROFESSIONS"] = ["Engineering"]
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        role = Role(name="Software Engineer", grade="Grade 7", profession="Legal")
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    response = test_client.post(
        f"/roles/{role_id}/edit",
        data={"name": "Software Engineer", "grade": "Grade 7", "profession": "Unknown"},
    )

    assert response.status_code == 200
    with app.app_context():
        role = db.session.get(Role, role_id)
        assert role is not None
        assert role.profession == "Legal"
