from datetime import datetime, timezone

from app import db
from app.models import Person, Role
from app.person.service import get_people


def test_get_people_filters_employment_independently_from_status(app):
    """GIVEN active and archived people of both employment types
    WHEN employment and status filters are applied
    THEN both filters are respected independently."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        permanent = Person(
            name="Permanent Person",
            email_address="permanent@example.com",
            location="London",
            employment_type="permanent",
            role_id=role.id,
        )
        contractor = Person(
            name="Contractor Person",
            email_address="contractor@example.com",
            location="London",
            employment_type="contractor",
            role_id=role.id,
        )
        archived_contractor = Person(
            name="Archived Contractor",
            email_address="archived@example.com",
            location="London",
            employment_type="contractor",
            role_id=role.id,
        )
        archived_contractor.archived_at = datetime.now(timezone.utc)
        db.session.add_all([permanent, contractor, archived_contractor])
        db.session.commit()

        active_contractors = get_people(status="active", employment_type="contractor", per_page=10)
        all_contractors = get_people(status="all", employment_type="contractor", per_page=10)

        assert [person.name for person in active_contractors.items] == ["Contractor Person"]
        assert [person.name for person in all_contractors.items] == [
            "Archived Contractor",
            "Contractor Person",
        ]


def test_get_people_sorts_employment_type_with_name_tiebreaker(app):
    """GIVEN people with both employment types WHEN sorted by employment type THEN type and name order are used."""
    with app.app_context():
        role = Role(name="Engineer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        people = [
            Person(
                name="Zed Contractor",
                email_address="zed@example.com",
                location="London",
                employment_type="contractor",
                role_id=role.id,
            ),
            Person(
                name="Beta Permanent",
                email_address="beta@example.com",
                location="London",
                employment_type="permanent",
                role_id=role.id,
            ),
            Person(
                name="Alpha Contractor",
                email_address="alpha@example.com",
                location="London",
                employment_type="contractor",
                role_id=role.id,
            ),
        ]
        db.session.add_all(people)
        db.session.commit()

        result = get_people(status="all", sort="employment_type", per_page=10)

        assert [person.name for person in result.items] == [
            "Alpha Contractor",
            "Zed Contractor",
            "Beta Permanent",
        ]
