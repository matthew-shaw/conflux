"""Person service module providing data access and business logic operations.

This module contains functions for CRUD operations on Person objects, handling
database interactions, transaction management, and query construction. All
database access from the person views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import nulls_last
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import db
from app.exceptions import ArchivedEntityError
from app.models import Person, Role, Team

logger = logging.getLogger(__name__)


def get_people(
    sort: str = "name",
    status: str = "active",
    employment: str = "all",
    page: int = 1,
    per_page: int = 25,
    profession: str | None = None,
    is_gap: bool | None = None,
) -> Pagination:
    """Retrieve a paginated list of people, including gaps unless filtered out.

    Gaps have no name or location, so they sort after named people and are
    ordered by role name amongst themselves. Gaps are never archived.
    """

    # Start the base SELECT statement
    query = db.select(Person).join(Person.role).options(selectinload(Person.role), selectinload(Person.team))

    sort_orders = {
        "name": (nulls_last(Person.name), Role.name, Person.id),
        "location": (nulls_last(Person.location), nulls_last(Person.name), Role.name, Person.id),
        "employment": (Person.employment, nulls_last(Person.name), Role.name, Person.id),
        "updated": (Person.updated_at.desc(),),
    }
    query = query.order_by(*sort_orders.get(sort, ()))

    status_filters = {
        "active": Person.archived_at.is_(None),
        "archived": Person.archived_at.is_not(None) & Person.is_gap.is_(False),
    }
    if (status_filter := status_filters.get(status)) is not None:
        query = query.where(status_filter)

    if is_gap is not None:
        query = query.where(Person.is_gap.is_(is_gap))

    if employment in Person.EMPLOYMENTS:
        query = query.where(Person.employment == employment)

    if profession:
        query = query.where(Person.role.has(Role.profession == profession))

    try:
        return db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False,
        )

    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(
            f"Database error retrieving people (sort={sort}, status={status}, employment={employment}, "
            f"profession={profession}, "
            f"page={page}, per_page={per_page})",
            exc_info=True,
        )
        raise


def get_active_people() -> list[Person]:
    """Retrieve all active real people, excluding gaps, for use as manager choices."""
    try:
        return list(
            db.session.execute(
                db.select(Person).order_by(Person.name).where(Person.archived_at.is_(None), Person.is_gap.is_(False))
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error retrieving all people", exc_info=True)
        raise


def get_person(id: UUID) -> Person:
    """Retrieve a person or gap by identifier, raising NoResultFound if absent."""
    try:
        return db.session.execute(db.select(Person).filter_by(id=id)).scalar_one()
    except NoResultFound:
        logger.debug(f"Person not found {id}", exc_info=True)
        raise


def get_gap(id: UUID) -> Person:
    """Retrieve a gap by identifier, raising NoResultFound if absent or a real person."""
    try:
        return db.session.execute(db.select(Person).filter_by(id=id, is_gap=True)).scalar_one()
    except NoResultFound:
        logger.debug(f"Gap not found {id}", exc_info=True)
        raise


def has_matching_gap(employment: str, team_id: UUID | None, role_id: UUID) -> bool:
    """Report whether an open gap exists for the employment type, team and role."""
    statement = (
        db.select(Person.id)
        .where(
            Person.is_gap.is_(True),
            Person.employment == employment,
            Person.team_id == team_id,
            Person.role_id == role_id,
        )
        .limit(1)
    )
    try:
        return db.session.scalar(statement) is not None
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error checking for a matching gap", exc_info=True)
        raise


def find_matching_gap(employment: str, team_id: UUID | None, role_id: UUID) -> Person | None:
    """Lock and return the lowest UUID gap matching the assignment, if any.

    Rows already locked by a concurrent fill are skipped, so two people cannot
    fill the same gap.
    """
    return db.session.scalar(
        db.select(Person)
        .where(
            Person.is_gap.is_(True),
            Person.employment == employment,
            Person.team_id == team_id,
            Person.role_id == role_id,
        )
        .order_by(Person.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def _lock_active_assignment(role_id: UUID, team_id: UUID | None) -> None:
    """Ensure the role and optional team exist and are active, raising NoResultFound otherwise."""
    db.session.execute(
        db.select(Role.id).where(Role.id == role_id, Role.archived_at.is_(None)).with_for_update()
    ).scalar_one()
    if team_id is not None:
        db.session.execute(
            db.select(Team.id).where(Team.id == team_id, Team.archived_at.is_(None)).with_for_update()
        ).scalar_one()


def create_gap(employment: str, role_id: UUID, team_id: UUID | None) -> Person:
    """Create a gap for an active role and optional active team."""
    try:
        _lock_active_assignment(role_id, team_id)
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
        logger.info(f"Created gap id={gap.id}")
        return gap
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.warning(f"Database error creating gap: {type(error).__name__}", exc_info=True)
        raise


def update_gap(id: UUID, employment: str, role_id: UUID, team_id: UUID | None) -> Person:
    """Change a gap's employment type, role and team without converting it to a person."""
    try:
        gap = get_gap(id)
        if gap.role_id != role_id or gap.team_id != team_id:
            _lock_active_assignment(role_id, team_id)
        gap.employment = employment
        gap.role_id = role_id
        gap.team_id = team_id
        db.session.commit()
        logger.info(f"Updated gap {id}")
        return gap
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.warning(f"Database error updating gap {id}: {type(error).__name__}", exc_info=True)
        raise


def delete_gap(id: UUID) -> None:
    """Permanently remove a gap; real people can only be archived."""
    try:
        gap = get_gap(id)
        db.session.delete(gap)
        db.session.commit()
        logger.info(f"Deleted gap {id}")
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.warning(f"Database error deleting gap {id}: {type(error).__name__}", exc_info=True)
        raise


def create_person(
    name: str,
    email_address: str,
    location: str,
    employment: str,
    role_id: UUID,
    team_id: UUID | None,
    manager_id: UUID | None,
    fill_gap: bool = False,
) -> Person:
    """Create a person, reusing a matching gap's row when asked to fill it.

    When `fill_gap` is set and a gap matches the employment type, team and role,
    that gap is converted into the new person rather than adding another row.
    """
    try:
        gap = find_matching_gap(employment, team_id, role_id) if fill_gap else None
        if gap is not None:
            person = gap
            person.is_gap = False
            person.name = name.title()
            person.email_address = email_address.lower()
            person.location = location
            person.manager_id = manager_id
            logger.info(f"Filled gap {gap.id}")
        else:
            person = Person(
                name=name.title(),
                email_address=email_address.lower(),
                location=location,
                employment=employment,
                role_id=role_id,
                team_id=team_id,
                manager_id=manager_id,
            )
            # Add the new person instance to the session
            db.session.add(person)
        # Attempt to commit the transaction to persist the person
        db.session.commit()
        logger.info(f"Created person: {name} (id={getattr(person, 'id', None)})")
        return person
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        logger.debug(f"IntegrityError creating person {name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error creating person {name}", exc_info=True)
        raise


def update_person(
    id: UUID,
    name: str,
    email_address: str,
    location: str,
    employment: str,
    role_id: UUID,
    team_id: UUID | None,
    manager_id: UUID | None,
    fill_gap: bool = False,
    leave_previous_gap: bool = False,
) -> None:
    """Update a person, filling or leaving gaps only when their assignment changes.

    When `fill_gap` is set and the employment type, team or role changes to match a
    gap, that gap is deleted. When `leave_previous_gap` is set and the person moves
    out of a team, a gap with their previous employment type and role is left in
    that previous team. Gaps themselves are edited with `update_gap`.
    """
    # Retrieve the person or raise 404 if not found
    person = get_person(id)
    if person.is_gap:
        logger.debug(f"Person {id} is a gap", exc_info=True)
        raise NoResultFound(f"Person {id} is a gap")
    # Prevent editing archived people
    if person.archived_at is not None:
        raise ArchivedEntityError(f"Cannot update archived person {id}")
    assignment_changed = (person.employment, person.team_id, person.role_id) != (employment, team_id, role_id)
    previous_employment, previous_team_id, previous_role_id = person.employment, person.team_id, person.role_id
    # Update the person's attributes with the new values
    person.name = name.title()
    person.email_address = email_address.lower()
    person.location = location
    person.employment = employment
    person.role_id = role_id
    person.team_id = team_id
    person.manager_id = manager_id
    try:
        if fill_gap and assignment_changed:
            gap = find_matching_gap(employment, team_id, role_id)
            if gap is not None:
                db.session.delete(gap)
                logger.info(f"Filled gap {gap.id} when updating person {id}")
        if leave_previous_gap and previous_team_id is not None and previous_team_id != team_id:
            left_gap = Person(
                name=None,
                email_address=None,
                location=None,
                employment=previous_employment,
                role_id=previous_role_id,
                team_id=previous_team_id,
                is_gap=True,
            )
            db.session.add(left_gap)
            db.session.flush()
            logger.info(f"Left gap {left_gap.id} for person {id}")
        # Commit the update transaction
        db.session.commit()
        logger.info(f"Updated person {id}")
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        logger.debug(f"IntegrityError updating person {id} to name={name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error updating person {id}", exc_info=True)
        raise


def archive_person(id: UUID) -> None:
    """Archive a real person, raising NoResultFound for gaps, which are deleted instead."""
    # Retrieve the person or raise 404 if not found
    person = get_person(id)
    if person.is_gap:
        logger.debug(f"Person {id} is a gap", exc_info=True)
        raise NoResultFound(f"Person {id} is a gap")
    # Set the archived_at timestamp to mark the person as archived
    person.archived_at = datetime.now(UTC)
    logger.info(f"Archiving person {id}")
    try:
        # Commit the archive action
        db.session.commit()
        logger.info(f"Archived person {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error archiving person {id}", exc_info=True)
        raise


def restore_person(id: UUID) -> None:
    """Restore an archived real person, raising NoResultFound for gaps."""
    # Retrieve the person or raise 404 if not found
    person = get_person(id)
    if person.is_gap:
        logger.debug(f"Person {id} is a gap", exc_info=True)
        raise NoResultFound(f"Person {id} is a gap")
    # Clear the archived_at timestamp to mark the person as active
    person.archived_at = None
    logger.info(f"Restoring person {id}")
    try:
        # Commit the restore action
        db.session.commit()
        logger.info(f"Restored person {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error restoring person {id}", exc_info=True)
        raise


def download_people() -> list[Person]:
    """Retrieve all real people for CSV export, excluding gaps."""
    try:
        return list(
            db.session.execute(
                db.select(Person)
                .where(Person.is_gap.is_(False))
                .options(
                    selectinload(Person.role),
                    selectinload(Person.team),
                    selectinload(Person.manager),
                )
                .order_by(Person.name)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error downloading people", exc_info=True)
        raise
