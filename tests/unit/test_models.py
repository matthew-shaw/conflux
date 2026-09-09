import uuid
from datetime import datetime, timezone

from app.models import Person, Role, Team


def test_role_active_people_returns_only_unarchived_people():
    """GIVEN a role with active and archived people
    WHEN active_people property is accessed
    THEN only unarchived people are returned."""
    role_id = uuid.uuid4()
    active_person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
    )
    archived_person.archived_at = datetime.now(timezone.utc)

    role = Role(name="Software Engineer", grade="Grade 7")
    role.people = [active_person, archived_person]

    assert role.active_people == [active_person]


def test_role_active_people_returns_empty_when_no_people():
    """GIVEN a role with no associated people
    WHEN active_people property is accessed
    THEN an empty list is returned."""
    role = Role(name="Product Manager", grade="Grade 6")
    role.people = []

    assert role.active_people == []


def test_role_to_dict_includes_only_active_people():
    """GIVEN a role with active and archived people
    WHEN to_dict is called with include_people=True
    THEN only active people are included in the serialized output."""
    role_id = uuid.uuid4()
    active_person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
    )
    archived_person.archived_at = datetime.now(timezone.utc)

    role = Role(name="Data Analyst", grade="Grade 5")
    role.people = [active_person, archived_person]

    data = role.to_dict(include_people=True)

    assert len(data["people"]) == 1
    assert data["people"][0]["name"] == "Alice"


def test_team_active_people_returns_only_unarchived_people():
    """GIVEN a team with active and archived people
    WHEN active_people property is accessed
    THEN only unarchived people are returned."""
    role_id = uuid.uuid4()
    team_id = uuid.uuid4()
    active_person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
        team_id=team_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
        team_id=team_id,
    )
    archived_person.archived_at = datetime.now(timezone.utc)

    team = Team(name="Platform Team")
    team.people = [active_person, archived_person]

    assert team.active_people == [active_person]


def test_team_active_people_returns_empty_when_no_people():
    """GIVEN a team with no associated people
    WHEN active_people property is accessed
    THEN an empty list is returned."""
    team = Team(name="Delivery Team")
    team.people = []

    assert team.active_people == []


def test_team_to_dict_includes_only_active_people():
    """GIVEN a team with active and archived people
    WHEN to_dict is called with include_people=True
    THEN only active people are included in the serialized output."""
    role_id = uuid.uuid4()
    team_id = uuid.uuid4()
    active_person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
        team_id=team_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
        employment_type="permanent",
        role_id=role_id,
        team_id=team_id,
    )
    archived_person.archived_at = datetime.now(timezone.utc)

    team = Team(name="Data Team")
    team.people = [active_person, archived_person]

    data = team.to_dict(include_people=True)

    assert len(data["people"]) == 1
    assert data["people"][0]["name"] == "Alice"


def test_person_to_dict_includes_employment_type_and_raw_name():
    """GIVEN a contractor person WHEN serialized THEN the raw name and employment type are preserved."""
    person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        employment_type="contractor",
        role_id=uuid.uuid4(),
    )

    data = person.to_dict()

    assert data["name"] == "Alice"
    assert data["employment_type"] == "contractor"
