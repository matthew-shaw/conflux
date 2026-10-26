"""Database integration coverage of gaps modelled as people."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from flask import Flask
from sqlalchemy.exc import NoResultFound

from app import db
from app.models import Person
from app.person.service import (
    archive_person,
    create_gap,
    create_person,
    delete_gap,
    download_people,
    find_matching_gap,
    get_active_people,
    get_gap,
    get_people,
    has_matching_gap,
    restore_person,
    update_gap,
    update_person,
)
from app.role.service import archive_role
from app.team.service import archive_team


def _count_people() -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(Person)) or 0


def _create_real_person(catalog: dict[str, UUID], team_key: str = "other_team") -> Person:
    return create_person(
        name="Real Person",
        email_address="real@example.com",
        location="london",
        employment="employee",
        role_id=catalog["role"],
        team_id=catalog[team_key],
        manager_id=None,
    )


@pytest.mark.parametrize("invalid", ["archived_team", "archived_role", "missing_team", "missing_role"])
def test_create_gap_rejects_inactive_or_unknown_parent(app: Flask, gap_catalog: dict[str, UUID], invalid: str) -> None:
    """
    GIVEN an archived or nonexistent team or role
    WHEN the service is asked to create a gap
    THEN it raises NoResultFound without persisting anything
    """
    team_id = gap_catalog["archived_team"] if invalid == "archived_team" else gap_catalog["team"]
    role_id = gap_catalog["archived_role"] if invalid == "archived_role" else gap_catalog["role"]
    if invalid == "missing_team":
        team_id = uuid4()
    if invalid == "missing_role":
        role_id = uuid4()
    with app.app_context():
        with pytest.raises(NoResultFound):
            create_gap("employee", role_id, team_id)
        assert _count_people() == 0


@pytest.mark.parametrize("with_team", [True, False])
def test_create_gap_has_no_personal_details(app: Flask, gap_catalog: dict[str, UUID], with_team: bool) -> None:
    """
    GIVEN an active role and an optional active team
    WHEN a gap is created
    THEN it is a person flagged as a gap with no name, email address, location or manager
    """
    team_id = gap_catalog["team"] if with_team else None
    with app.app_context():
        gap = create_gap("contractor", gap_catalog["role"], team_id)
        stored = get_gap(gap.id)
        assert stored.is_gap is True
        assert (stored.name, stored.email_address, stored.location, stored.manager_id) == (None, None, None, None)
        assert (stored.employment, stored.role_id, stored.team_id) == ("contractor", gap_catalog["role"], team_id)
        assert stored.display_name == "Gap"
        assert stored.to_dict()["is_gap"] is True


@pytest.mark.parametrize("missing", ["name", "location"])
def test_create_person_requires_person_details(app: Flask, gap_catalog: dict[str, UUID], missing: str) -> None:
    """
    GIVEN a real person without a name or location
    WHEN the service is asked to create the person
    THEN it rejects the invalid person shape before persistence
    """
    with app.app_context():
        details: dict[str, str | None] = {"name": "Someone", "location": "london"}
        details[missing] = None
        with pytest.raises(ValueError, match="name and location"):
            create_person(
                name=details["name"],
                email_address="someone@example.com",
                location=details["location"],
                employment="employee",
                role_id=gap_catalog["role"],
                team_id=None,
                manager_id=None,
            )
        assert _count_people() == 0


def test_matching_requires_employment_team_and_role(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN two identical gaps and gaps for other assignments
    WHEN a matching gap is looked up
    THEN only exact employment, team and role matches are found, lowest UUID first
    """
    with app.app_context():
        first = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        second = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        create_gap("contractor", gap_catalog["other_role"], gap_catalog["other_team"])
        teamless_gap = create_gap("employee", gap_catalog["role"], None)
        assert has_matching_gap("employee", gap_catalog["team"], gap_catalog["role"])
        assert not has_matching_gap("contractor", gap_catalog["team"], gap_catalog["role"])
        assert not has_matching_gap("employee", gap_catalog["team"], gap_catalog["other_role"])
        assert has_matching_gap("employee", None, gap_catalog["role"])
        match = find_matching_gap("employee", gap_catalog["team"], gap_catalog["role"])
        assert match is not None
        assert match.id == min(first.id, second.id)
        teamless_match = find_matching_gap("employee", None, gap_catalog["role"])
        assert teamless_match is not None
        assert teamless_match.id == teamless_gap.id


def test_create_person_filling_gap_reuses_its_row(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a gap matching a new person's employment, team and role
    WHEN the person is created with fill selected
    THEN the gap row becomes the person and no extra row is added
    """
    with app.app_context():
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        gap_id = gap.id
        manager = _create_real_person(gap_catalog)
        person = create_person(
            name="new starter",
            email_address="New@Example.com",
            location="london",
            employment="employee",
            role_id=gap_catalog["role"],
            team_id=gap_catalog["team"],
            manager_id=manager.id,
            fill_gap=True,
        )
        assert person.id == gap_id
        assert _count_people() == 2
        stored = db.session.get(Person, gap_id)
        assert stored is not None
        assert stored.is_gap is False
        assert (stored.name, stored.email_address, stored.location, stored.manager_id) == (
            "New Starter",
            "new@example.com",
            "london",
            manager.id,
        )


@pytest.mark.parametrize(
    ("employment", "fill_gap"),
    [("employee", False), ("contractor", True)],
)
def test_create_person_without_fill_or_match_adds_row(
    app: Flask, gap_catalog: dict[str, UUID], employment: str, fill_gap: bool
) -> None:
    """
    GIVEN an employee gap
    WHEN a person is created without fill, or with a different employment type
    THEN a new row is created and the gap remains
    """
    with app.app_context():
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        person = create_person(
            name="New Starter",
            email_address="new@example.com",
            location="london",
            employment=employment,
            role_id=gap_catalog["role"],
            team_id=gap_catalog["team"],
            manager_id=None,
            fill_gap=fill_gap,
        )
        assert person.id != gap.id
        assert get_gap(gap.id).is_gap is True
        assert _count_people() == 2


@pytest.mark.parametrize(("fill_gap", "gap_remains"), [(True, False), (False, True)])
def test_update_person_into_matching_gap(
    app: Flask, gap_catalog: dict[str, UUID], fill_gap: bool, gap_remains: bool
) -> None:
    """
    GIVEN a person and a gap in another team for their role
    WHEN the person moves into that team with or without fill
    THEN the gap is deleted only when filling
    """
    with app.app_context():
        person = _create_real_person(gap_catalog)
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        gap_id = gap.id
        update_person(
            id=person.id,
            name="Real Person",
            email_address="real@example.com",
            location="london",
            employment="employee",
            role_id=gap_catalog["role"],
            team_id=gap_catalog["team"],
            manager_id=None,
            fill_gap=fill_gap,
        )
        assert (db.session.get(Person, gap_id) is not None) is gap_remains
        assert db.session.get(Person, person.id) is not None


def test_update_person_changing_employment_fills_gap(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN an employee and a contractor gap for the same team and role
    WHEN the person becomes a contractor with fill selected
    THEN the contractor gap is deleted
    """
    with app.app_context():
        person = _create_real_person(gap_catalog, team_key="team")
        gap = create_gap("contractor", gap_catalog["role"], gap_catalog["team"])
        gap_id = gap.id
        update_person(
            id=person.id,
            name="Real Person",
            email_address="real@example.com",
            location="london",
            employment="contractor",
            role_id=gap_catalog["role"],
            team_id=gap_catalog["team"],
            manager_id=None,
            fill_gap=True,
        )
        assert db.session.get(Person, gap_id) is None


def test_update_person_leaving_gap_creates_gap_person(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a contractor in a team
    WHEN they move team and choose to leave a gap
    THEN a gap with their previous employment, role and team is created
    """
    with app.app_context():
        person = create_person(
            name="Mover",
            email_address="mover@example.com",
            location="london",
            employment="contractor",
            role_id=gap_catalog["role"],
            team_id=gap_catalog["team"],
            manager_id=None,
        )
        update_person(
            id=person.id,
            name="Mover",
            email_address="mover@example.com",
            location="london",
            employment="employee",
            role_id=gap_catalog["other_role"],
            team_id=gap_catalog["other_team"],
            manager_id=None,
            leave_previous_gap=True,
        )
        gaps = db.session.execute(db.select(Person).where(Person.is_gap.is_(True))).scalars().all()
        assert [(gap.employment, gap.role_id, gap.team_id) for gap in gaps] == [
            ("contractor", gap_catalog["role"], gap_catalog["team"])
        ]


def test_update_gap_changes_assignment_only(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a gap
    WHEN its employment, role and team are updated, including clearing the team
    THEN those fields change and it remains a gap without personal details
    """
    with app.app_context():
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        update_gap(gap.id, "contractor", gap_catalog["other_role"], None)
        stored = get_gap(gap.id)
        assert (stored.employment, stored.role_id, stored.team_id) == ("contractor", gap_catalog["other_role"], None)
        assert stored.is_gap is True
        assert (stored.name, stored.location) == (None, None)


def test_update_gap_rejects_real_people_and_archived_roles(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a real person and a gap
    WHEN update_gap targets the person, or moves the gap to an archived role
    THEN NoResultFound is raised
    """
    with app.app_context():
        person = _create_real_person(gap_catalog)
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        with pytest.raises(NoResultFound):
            update_gap(person.id, "employee", gap_catalog["role"], None)
        with pytest.raises(NoResultFound):
            update_gap(gap.id, "employee", gap_catalog["archived_role"], None)
        assert get_gap(gap.id).role_id == gap_catalog["role"]


def test_gaps_cannot_be_archived_restored_or_updated_as_people(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a gap
    WHEN it is archived, restored or updated as a person
    THEN NoResultFound is raised and it is unchanged
    """
    with app.app_context():
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        with pytest.raises(NoResultFound):
            archive_person(gap.id)
        with pytest.raises(NoResultFound):
            restore_person(gap.id)
        with pytest.raises(NoResultFound):
            update_person(
                id=gap.id,
                name="Name",
                email_address="name@example.com",
                location="london",
                employment="employee",
                role_id=gap_catalog["role"],
                team_id=None,
                manager_id=None,
            )
        assert get_gap(gap.id).archived_at is None


def test_delete_gap_removes_only_gaps(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a gap and a real person
    WHEN delete_gap is called for each
    THEN the gap is deleted and the person is not
    """
    with app.app_context():
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        gap_id = gap.id
        person = _create_real_person(gap_catalog)
        delete_gap(gap_id)
        assert db.session.get(Person, gap_id) is None
        with pytest.raises(NoResultFound):
            delete_gap(person.id)
        assert db.session.get(Person, person.id) is not None


def test_listings_treat_gaps_appropriately(app: Flask, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a real person, an archived person and a gap
    WHEN people are listed, filtered, offered as managers or downloaded
    THEN gaps are listed after named people but never archived, managers or downloaded
    """
    with app.app_context():
        person = _create_real_person(gap_catalog)
        archived = create_person(
            name="Archived Person",
            email_address="archived@example.com",
            location="london",
            employment="employee",
            role_id=gap_catalog["role"],
            team_id=None,
            manager_id=None,
        )
        archived.archived_at = datetime.now(UTC)
        db.session.commit()
        gap = create_gap("employee", gap_catalog["role"], gap_catalog["team"])

        assert [item.id for item in get_people().items] == [person.id, gap.id]
        assert [item.id for item in get_people(is_gap=True).items] == [gap.id]
        assert [item.id for item in get_people(is_gap=False).items] == [person.id]
        assert [item.id for item in get_people(status="archived").items] == [archived.id]
        assert gap.id not in [item.id for item in get_active_people()]
        assert gap.id not in [item.id for item in download_people()]


@pytest.mark.parametrize("archive", [archive_team, archive_role])
def test_archiving_parent_deletes_its_gaps(app: Flask, gap_catalog: dict[str, UUID], archive) -> None:
    """
    GIVEN gaps for a team and role and an unrelated gap
    WHEN the team or role is archived
    THEN its gaps are deleted and the unrelated gap remains
    """
    with app.app_context():
        related = create_gap("employee", gap_catalog["role"], gap_catalog["team"])
        unrelated = create_gap("employee", gap_catalog["other_role"], gap_catalog["other_team"])
        related_id, unrelated_id = related.id, unrelated.id
        archive(gap_catalog["team"] if archive is archive_team else gap_catalog["role"])
        assert db.session.get(Person, related_id) is None
        assert db.session.get(Person, unrelated_id) is not None
