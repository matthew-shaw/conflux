from datetime import datetime, timezone
from types import SimpleNamespace

from app import db
from app.models import Person, Role, Team
from app.person import ui as person_ui
from app.person.forms import PersonForm
from app.search.service import search_entries


def test_person_form_requires_employment_type(app):
    """GIVEN a person form without employment type
    WHEN validated
    THEN validation fails."""
    with app.test_request_context("/people/new", method="POST"):
        form = PersonForm(data={"employment_type": ""})
        form.location.choices = [("london", "London")]
        form.role.choices = [("role", "Role")]
        form.team.choices = [("", "Select a team")]
        form.manager.choices = [("", "Select a manager")]

        assert form.validate() is False
        assert form.employment_type.errors == ["Select an employment type"]


def test_create_and_edit_person_persist_employment_type(app, test_client):
    """GIVEN a valid person submission
    WHEN created and edited
    THEN employment type is persisted."""
    app.config["DOMAIN"] = "example.com"
    app.config["LOCATIONS"] = ["London"]
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.commit()
        role_id = str(role.id)

    response = test_client.post(
        "/people/new",
        data={
            "name": "Contractor Person",
            "email_address": "contractor@example.com",
            "location": "london",
            "employment_type": "contractor",
            "role": role_id,
            "team": "",
            "manager": "",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        person = db.session.query(Person).one()
        person_id = person.id
        assert person.employment_type == "contractor"

    response = test_client.post(
        f"/people/{person_id}/edit",
        data={
            "name": "Contractor Person",
            "email_address": "contractor@example.com",
            "location": "london",
            "employment_type": "permanent",
            "role": role_id,
            "team": "",
            "manager": "",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Person, person_id).employment_type == "permanent"


def test_people_list_preserves_employment_filter_in_json_link(app, test_client):
    """GIVEN a filtered people list
    WHEN rendered
    THEN the JSON link retains the filter and sort."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        db.session.add(
            Person(
                name="Contractor Person",
                email_address="contractor@example.com",
                location="London",
                employment_type="contractor",
                role_id=role.id,
            )
        )
        db.session.commit()

    response = test_client.get("/people/?sort=employment_type&status=all&employment_type=contractor&per_page=10")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "sort=employment_type" in body
    assert "status=all" in body
    assert "employment_type=contractor" in body


def test_people_api_filters_by_employment_type(app, test_client):
    """GIVEN permanent and contractor people
    WHEN the API is filtered
    THEN only the requested type is returned."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        db.session.add_all(
            [
                Person(
                    name="Permanent Person",
                    email_address="permanent@example.com",
                    location="London",
                    employment_type="permanent",
                    role_id=role.id,
                ),
                Person(
                    name="Contractor Person",
                    email_address="contractor@example.com",
                    location="London",
                    employment_type="contractor",
                    role_id=role.id,
                ),
            ]
        )
        db.session.commit()

    response = test_client.get("/api/v1/people/?employment_type=contractor")

    assert response.status_code == 200
    data = response.get_json()
    assert [person["name"] for person in data] == ["Contractor Person"]
    assert data[0]["employment_type"] == "contractor"


def test_people_profession_filter_supports_role_changes_and_combined_controls(app, test_client):
    """
    GIVEN people assigned to matching, unassigned, and archived roles
    WHEN the People page and API use an encoded profession with existing filters
    THEN role changes affect results and all links retain the profession filter.
    """
    app.config["PROFESSIONS"] = ["Engineering / R&D", "Product"]
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        engineering = Role(name="Engineer", grade="Grade 7", profession="Engineering / R&D")
        product = Role(name="Product Manager", grade="Grade 6", profession="Product")
        unassigned = Role(name="Analyst", grade="Grade 5")
        db.session.add_all([engineering, product, unassigned])
        db.session.flush()
        people = [
            Person(
                name="Alice Engineer",
                email_address="alice-engineer@example.com",
                location="London",
                employment_type="contractor",
                role_id=engineering.id,
            ),
            Person(
                name="Bob Engineer",
                email_address="bob-engineer@example.com",
                location="London",
                employment_type="permanent",
                role_id=engineering.id,
            ),
            Person(
                name="Cara Product",
                email_address="cara-product@example.com",
                location="London",
                employment_type="contractor",
                role_id=product.id,
            ),
            Person(
                name="Dan Unassigned",
                email_address="dan-unassigned@example.com",
                location="London",
                employment_type="contractor",
                role_id=unassigned.id,
            ),
        ]
        archived = Person(
            name="Erin Archived",
            email_address="erin-archived@example.com",
            location="London",
            employment_type="contractor",
            role_id=engineering.id,
        )
        archived.archived_at = datetime.now(timezone.utc)
        db.session.add_all([*people, archived])
        db.session.commit()
        engineering.profession = "Product"
        db.session.commit()

    query = "profession=Product&status=active&employment_type=contractor&per_page=1"
    response = test_client.get(f"/people/?{query}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Alice Engineer" in body
    assert "Cara Product" not in body
    assert "profession=Product" in body
    assert "employment_type=contractor" in body

    response = test_client.get(f"/api/v1/people/?{query}")

    assert response.status_code == 200
    assert [person["name"] for person in response.get_json()] == ["Alice Engineer"]

    response = test_client.get("/api/v1/people/?profession=Missing&status=all")

    assert response.status_code == 200
    assert response.get_json() == []


def test_person_detail_and_search_use_raw_contractor_name(app, test_client):
    """GIVEN a contractor person
    WHEN detail and search are requested
    THEN the raw name is presented."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        person = Person(
            name="Contractor Person",
            email_address="contractor@example.com",
            location="London",
            employment_type="contractor",
            role_id=role.id,
        )
        db.session.add(person)
        db.session.commit()
        person_id = person.id

        results = search_entries("Contractor")
        assert results[0]["name"] == "Contractor Person"

    response = test_client.get(f"/people/{person_id}")

    assert response.status_code == 200
    assert b"Contractor Person" in response.data
    assert b"Contractor Person (C)" not in response.data


def test_people_tables_show_employment_type_and_raw_names(app, test_client):
    """GIVEN a contractor person
    WHEN people, role, and team pages are viewed
    THEN employment is a separate column."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        team = Team(name="Engineering")
        db.session.add_all([role, team])
        db.session.flush()
        person = Person(
            name="Contractor Person",
            email_address="contractor@example.com",
            location="London",
            employment_type="contractor",
            role_id=role.id,
            team_id=team.id,
        )
        db.session.add(person)
        db.session.commit()
        role_id = role.id
        team_id = team.id

    for url in ("/people/", f"/roles/{role_id}", f"/teams/{team_id}"):
        response = test_client.get(url)
        assert response.status_code == 200
        assert b"Employment type" in response.data
        assert b"Contractor" in response.data
        assert b"Contractor Person" in response.data
        assert b"Contractor Person (C)" not in response.data


def test_people_csv_includes_employment_type_and_raw_names(monkeypatch, test_client):
    """GIVEN a contractor export
    WHEN CSV is downloaded
    THEN employment type and raw names are included."""
    contractor = SimpleNamespace(
        id="1",
        name="Contractor Person",
        employment_type="contractor",
        email_address="contractor@example.com",
        role=SimpleNamespace(id="role-1", name="Engineer", profession="Engineering"),
        team=None,
        location="london",
        manager=None,
        updated_at=datetime.now(timezone.utc),
        archived_at=None,
    )
    monkeypatch.setattr(person_ui, "download_people", lambda: [contractor])

    response = test_client.get("/people/download")

    assert response.status_code == 200
    csv_data = response.get_data(as_text=True)
    assert "ID,NAME,EMPLOYMENT_TYPE,EMAIL_ADDRESS,ROLE_ID,ROLE_NAME,PROFESSION" in csv_data
    assert "1,Contractor Person,contractor,contractor@example.com,role-1,Engineer,Engineering" in csv_data
