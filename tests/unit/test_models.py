from datetime import datetime, timezone
import uuid

from app.models import Person, Role


def test_role_active_people_returns_only_unarchived_people():
    """GIVEN a role with active and archived people
    WHEN active_people property is accessed
    THEN only unarchived people are returned."""
    role_id = uuid.uuid4()
    active_person = Person(
        name="Alice",
        email_address="alice@example.com",
        location="London",
        role_id=role_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
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
        role_id=role_id,
    )
    active_person.archived_at = None

    archived_person = Person(
        name="Bob",
        email_address="bob@example.com",
        location="London",
        role_id=role_id,
    )
    archived_person.archived_at = datetime.now(timezone.utc)

    role = Role(name="Data Analyst", grade="Grade 5")
    role.people = [active_person, archived_person]

    data = role.to_dict(include_people=True)

    assert len(data["people"]) == 1
    assert data["people"][0]["name"] == "Alice"
