"""Functional coverage for filling and leaving gap people through person forms and transactions."""

from uuid import UUID

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Person, Role
from app.person.service import create_person, get_person, update_person


def _submission(role_id: UUID, team_id: UUID | None) -> dict[str, str]:
    """Return a valid new person submission."""
    return {
        "name": "New Person",
        "email_address": "new@example.com",
        "location": "london",
        "employment": "employee",
        "role": str(role_id),
        "team": str(team_id) if team_id else "",
        "manager": "",
    }


def _real_people_count() -> int:
    """Count people who are not gaps."""
    return db.session.scalar(db.select(db.func.count()).select_from(Person).where(Person.is_gap.is_(False)))


def _all_gaps_count() -> int:
    """Count every open gap."""
    return db.session.scalar(db.select(db.func.count()).select_from(Person).where(Person.is_gap.is_(True)))


def _add_gap(team_id: UUID | None, role_id: UUID, employment: str = "employee") -> UUID:
    """Persist a gap person and return its identifier."""
    gap = Person(
        name=None,
        email_address=None,
        location=None,
        employment=employment,
        role_id=role_id,
        team_id=team_id,
        is_gap=True,
    )
    db.session.add(gap)
    db.session.commit()
    return gap.id


@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize("choice,remaining", [("yes", 1), ("no", 2)])
def test_matching_assignment_requires_explicit_choice(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID], editing: bool, choice: str, remaining: int
) -> None:
    """
    GIVEN a matching gap for a new or changed person assignment
    WHEN the person is submitted and then an explicit choice is submitted
    THEN no initial save occurs and only filling removes a gap
    """
    role_id, team_id, person_id = _seed
    data = _submission(role_id, team_id)
    path = f"/people/{person_id}/edit" if editing else "/people/new"
    response = test_client.post(path, data=data)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Fill the gap?" in body
    assert "Yes" in body
    assert 'value="new@example.com"' in body
    with app.app_context():
        assert _real_people_count() == 1
        assert get_person(person_id).team_id != team_id
        assert _all_gaps_count() == 2

    data.update(fill_gap=choice)
    if editing:
        data.update(leave_gap="no")
    response = test_client.post(path, data=data)
    assert response.status_code == 302
    with app.app_context():
        assert _real_people_count() == (1 if editing else 2)
        assert _all_gaps_count() == remaining


def test_teamless_gap_can_be_filled(app: Flask, test_client: FlaskClient, gap_catalog: dict[str, UUID]) -> None:
    """
    GIVEN a teamless gap for a role
    WHEN a person is created without a team and filling existing gaps is confirmed
    THEN the teamless gap is converted into the person
    """
    app.config["LOCATIONS"] = ["London"]
    role_id = gap_catalog["role"]
    with app.app_context():
        gap_id = _add_gap(None, role_id)

    data = _submission(role_id, None)
    response = test_client.post("/people/new", data=data)
    assert response.status_code == 200
    assert "Fill the gap?" in response.get_data(as_text=True)

    response = test_client.post("/people/new", data={**data, "fill_gap": "yes"}, follow_redirects=True)
    assert response.status_code == 200
    assert response.request.path == "/people/"
    with app.app_context():
        gap = db.session.get(Person, gap_id)
        assert gap is not None
        assert gap.is_gap is False
        assert gap.team_id is None
        assert gap.role_id == role_id
        assert _all_gaps_count() == 0
        assert _real_people_count() == 1


def test_create_form_does_not_show_fill_gap_question_initially(
    test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN a matching gap exists
    WHEN the add person form is first opened
    THEN the fill-gap question is not shown
    """
    response = test_client.get("/people/new")

    assert response.status_code == 200
    assert "Fill the gap?" not in response.get_data(as_text=True)


def _gap_count(team_id: UUID | None, role_id: UUID) -> int:
    """Count open gaps for one team and role."""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Person)
        .where(Person.is_gap.is_(True), Person.team_id == team_id, Person.role_id == role_id)
    )


def test_unchanged_team_does_not_require_leave_gap_answer(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN an existing person assigned to a team
    WHEN an edit keeping the same team is submitted without answering
    THEN the person is saved and no gap is left
    """
    role_id, _, person_id = _seed
    with app.app_context():
        team_id = get_person(person_id).team_id
    response = test_client.post(f"/people/{person_id}/edit", data=_submission(role_id, team_id))
    assert response.status_code == 302
    with app.app_context():
        assert _all_gaps_count() == 2


def test_changing_team_requires_leave_gap_choice(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN an existing person assigned to a team
    WHEN their team is changed without answering whether to leave a gap
    THEN an error is shown and the person is not updated
    """
    role_id, _, person_id = _seed
    with app.app_context():
        previous_team_id = get_person(person_id).team_id
    response = test_client.post(f"/people/{person_id}/edit", data=_submission(role_id, None))
    assert response.status_code == 200
    assert "Leave a gap" in response.get_data(as_text=True)
    with app.app_context():
        assert get_person(person_id).team_id == previous_team_id
        assert _all_gaps_count() == 2


@pytest.mark.parametrize("choice,expected", [("yes", 2), ("no", 1)])
def test_changing_team_leaves_gap_when_chosen(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID], choice: str, expected: int
) -> None:
    """
    GIVEN an existing person assigned to a team
    WHEN their team is changed and leaving a gap is answered
    THEN a gap for their role is left in the previous team only when yes is selected
    """
    role_id, _, person_id = _seed
    with app.app_context():
        previous_team_id = get_person(person_id).team_id
    response = test_client.post(f"/people/{person_id}/edit", data={**_submission(role_id, None), "leave_gap": choice})
    assert response.status_code == 302
    with app.app_context():
        assert get_person(person_id).team_id is None
        assert _gap_count(previous_team_id, role_id) == expected


def test_leaving_gap_uses_previous_role(app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]) -> None:
    """
    GIVEN an existing person assigned to a team and role
    WHEN both their team and role are changed and leaving a gap is selected
    THEN the gap left in the previous team is for their previous role
    """
    previous_role_id, _, person_id = _seed
    with app.app_context():
        previous_team_id = get_person(person_id).team_id
        role = Role(name="Designer", grade="Grade 7")
        db.session.add(role)
        db.session.commit()
        new_role_id = role.id
    response = test_client.post(
        f"/people/{person_id}/edit", data={**_submission(new_role_id, None), "leave_gap": "yes"}
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_person(person_id).role_id == new_role_id
        assert _gap_count(previous_team_id, previous_role_id) == 2
        assert _gap_count(previous_team_id, new_role_id) == 0


def test_service_unchanged_team_never_leaves_gap(app: Flask, _seed: tuple[UUID, UUID, UUID]) -> None:
    """
    GIVEN an existing person assigned to a team
    WHEN the service updates them within the same team with leaving a gap requested
    THEN no gap is added
    """
    role_id, _, person_id = _seed
    with app.app_context():
        person = get_person(person_id)
        update_person(
            person_id,
            "Renamed Person",
            "existing@example.com",
            "london",
            "employee",
            role_id,
            person.team_id,
            None,
            leave_previous_gap=True,
        )
        assert _all_gaps_count() == 2


def test_unrelated_edit_does_not_offer_or_consume_gap(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN an existing person whose current assignment has a gap
    WHEN only unrelated details are changed with a fill value submitted
    THEN the person is saved without offering or consuming a gap
    """
    role_id, _, person_id = _seed
    with app.app_context():
        team_id = get_person(person_id).team_id
    response = test_client.post(f"/people/{person_id}/edit", data={**_submission(role_id, team_id), "fill_gap": "yes"})
    assert response.status_code == 302
    with app.app_context():
        assert get_person(person_id).name == "New Person"
        assert _all_gaps_count() == 2


def test_unassigned_person_has_no_gap_choice(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN gaps associated with teams
    WHEN a person is created without a team
    THEN the person is saved directly and no gap is consumed
    """
    role_id, _, _ = _seed
    response = test_client.post("/people/new", data=_submission(role_id, None))
    assert response.status_code == 302
    with app.app_context():
        assert _all_gaps_count() == 2


@pytest.mark.parametrize("editing", [False, True])
def test_failed_save_rolls_back_gap(app: Flask, _seed: tuple[UUID, UUID, UUID], editing: bool) -> None:
    """
    GIVEN a matching gap and an email address already used by another person
    WHEN a create or assignment update fails after requesting a fill
    THEN the person changes and gap deletion are rolled back together
    """
    role_id, team_id, person_id = _seed
    with app.app_context():
        other = create_person("Other Person", "other@example.com", "london", "employee", role_id, None, None)
        other_id = other.id
        with pytest.raises(IntegrityError):
            if editing:
                update_person(
                    other_id,
                    "Changed Person",
                    "existing@example.com",
                    "london",
                    "employee",
                    role_id,
                    team_id,
                    None,
                    fill_gap=True,
                )
            else:
                create_person(
                    "Duplicate Person",
                    "existing@example.com",
                    "london",
                    "employee",
                    role_id,
                    team_id,
                    None,
                    fill_gap=True,
                )
        assert _all_gaps_count() == 2
        assert _real_people_count() == 2
        assert get_person(other_id).team_id is None
        assert get_person(person_id).name == "Existing Person"


def test_service_unchanged_assignment_never_fills(app: Flask, _seed: tuple[UUID, UUID, UUID]) -> None:
    """
    GIVEN an existing person with a matching gap on their current assignment
    WHEN the service updates unrelated details with filling requested
    THEN no gap is consumed
    """
    role_id, _, person_id = _seed
    with app.app_context():
        person = get_person(person_id)
        update_person(
            person_id,
            "Renamed Person",
            "existing@example.com",
            "london",
            "employee",
            role_id,
            person.team_id,
            None,
            fill_gap=True,
        )
        assert _all_gaps_count() == 2


def test_role_only_edit_requires_choice(app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]) -> None:
    """
    GIVEN a gap for a different role in a person's current team
    WHEN only their role assignment changes
    THEN the gap choice is required before the person is updated
    """
    _, _, person_id = _seed
    with app.app_context():
        person = get_person(person_id)
        team_id = person.team_id
        assert team_id is not None
        original_role_id = person.role_id
        role = Role(name="Designer", grade="Grade 7")
        db.session.add(role)
        db.session.flush()
        role_id = role.id
        _add_gap(team_id, role_id)
    response = test_client.post(f"/people/{person_id}/edit", data=_submission(role_id, team_id))
    assert response.status_code == 200
    assert "Fill the gap?" in response.get_data(as_text=True)
    with app.app_context():
        assert get_person(person_id).role_id == original_role_id


def test_fill_consumes_only_lowest_uuid_gap(app: Flask, _seed: tuple[UUID, UUID, UUID]) -> None:
    """
    GIVEN multiple gaps for the same employment type, team and role
    WHEN creating a person with filling requested
    THEN exactly the lowest UUID matching gap becomes the new person
    """
    role_id, team_id, _ = _seed
    with app.app_context():
        _add_gap(team_id, role_id)
        gaps = list(
            db.session.scalars(
                db.select(Person).where(Person.is_gap.is_(True), Person.team_id == team_id).order_by(Person.id)
            )
        )
        first_id, second_id = (gap.id for gap in gaps)
        person = create_person(
            "New Person", "new@example.com", "london", "employee", role_id, team_id, None, fill_gap=True
        )
        assert person.id == first_id
        assert get_person(first_id).is_gap is False
        assert get_person(second_id).is_gap is True


def test_disappearing_gap_does_not_prevent_save(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN a fill choice displayed for an existing gap
    WHEN that gap disappears before the choice is submitted
    THEN the person is saved without consuming a different assignment's gap
    """
    role_id, team_id, _ = _seed
    data = _submission(role_id, team_id)
    with app.app_context():
        gap = db.session.execute(
            db.select(Person).where(Person.is_gap.is_(True), Person.team_id == team_id)
        ).scalar_one()
        db.session.delete(gap)
        db.session.commit()
    data.update(fill_gap="yes")
    response = test_client.post("/people/new", data=data)
    assert response.status_code == 302
    with app.app_context():
        assert _real_people_count() == 2
        assert _all_gaps_count() == 1


@pytest.mark.parametrize("editing", [False, True])
def test_commit_failure_restores_flushed_gap_deletion(
    app: Flask, monkeypatch: pytest.MonkeyPatch, _seed: tuple[UUID, UUID, UUID], editing: bool
) -> None:
    """
    GIVEN a matching gap selected for filling in a person transaction
    WHEN committing fails after the gap deletion and person changes have flushed
    THEN rollback restores both the gap and the original person state
    """
    role_id, team_id, person_id = _seed
    with app.app_context():

        def fail_commit() -> None:
            db.session.flush()
            assert _all_gaps_count() == 1
            raise IntegrityError("commit failed", {}, RuntimeError("transaction failed"))

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(IntegrityError):
            if editing:
                update_person(
                    person_id,
                    "Changed Person",
                    "new@example.com",
                    "london",
                    "employee",
                    role_id,
                    team_id,
                    None,
                    fill_gap=True,
                )
            else:
                create_person(
                    "New Person",
                    "new@example.com",
                    "london",
                    "employee",
                    role_id,
                    team_id,
                    None,
                    fill_gap=True,
                )
        assert _all_gaps_count() == 2
        assert _real_people_count() == 1
        assert get_person(person_id).name == "Existing Person"
        assert get_person(person_id).team_id != team_id


@pytest.mark.parametrize("editing", [False, True])
def test_gap_with_other_employment_type_is_not_offered(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID], editing: bool
) -> None:
    """
    GIVEN only employee gaps for a team and role
    WHEN a contractor is created or moved into that team and role
    THEN no fill choice is required and the gaps remain
    """
    role_id, team_id, person_id = _seed
    data = {**_submission(role_id, team_id), "employment": "contractor", "leave_gap": "no"}
    path = f"/people/{person_id}/edit" if editing else "/people/new"
    response = test_client.post(path, data=data)
    assert response.status_code == 302
    with app.app_context():
        assert _all_gaps_count() == 2


def test_changing_employment_type_offers_matching_gap(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN a contractor gap in a person's current team and role
    WHEN only their employment type changes to contractor and filling is chosen
    THEN the choice is required first and the contractor gap is then deleted
    """
    role_id, _, person_id = _seed
    with app.app_context():
        team_id = get_person(person_id).team_id
        gap_id = _add_gap(team_id, role_id, employment="contractor")
    data = {**_submission(role_id, team_id), "employment": "contractor"}
    response = test_client.post(f"/people/{person_id}/edit", data=data)
    assert response.status_code == 200
    assert "Fill the gap?" in response.get_data(as_text=True)
    response = test_client.post(f"/people/{person_id}/edit", data={**data, "fill_gap": "yes"})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Person, gap_id) is None
        assert get_person(person_id).employment == "contractor"


def test_created_person_reuses_filled_gap_row(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN a matching employee gap in a team
    WHEN a new person is created in that team choosing to fill it
    THEN the gap row is converted into the new person rather than adding a row
    """
    role_id, team_id, _ = _seed
    with app.app_context():
        gap_id = db.session.execute(
            db.select(Person.id).where(Person.is_gap.is_(True), Person.team_id == team_id)
        ).scalar_one()
    response = test_client.post("/people/new", data={**_submission(role_id, team_id), "fill_gap": "yes"})
    assert response.status_code == 302
    with app.app_context():
        person = get_person(gap_id)
        assert person.is_gap is False
        assert (person.name, person.email_address, person.location) == ("New Person", "new@example.com", "london")
        assert db.session.scalar(db.select(db.func.count()).select_from(Person)) == 3


def test_leaving_gap_keeps_previous_employment_type(
    app: Flask, test_client: FlaskClient, _seed: tuple[UUID, UUID, UUID]
) -> None:
    """
    GIVEN an employee assigned to a team
    WHEN they become a contractor in no team and choose to leave a gap
    THEN the gap left behind is for an employee
    """
    role_id, _, person_id = _seed
    with app.app_context():
        previous_team_id = get_person(person_id).team_id
    data = {**_submission(role_id, None), "employment": "contractor", "leave_gap": "yes"}
    response = test_client.post(f"/people/{person_id}/edit", data=data)
    assert response.status_code == 302
    with app.app_context():
        left = db.session.scalars(
            db.select(Person).where(Person.is_gap.is_(True), Person.team_id == previous_team_id)
        ).all()
        assert sorted(gap.employment for gap in left) == ["employee", "employee"]
