"""Person service module providing data access and business logic operations.

This module contains functions for CRUD operations on Person objects, handling
database interactions, transaction management, and query construction. All
database access from the person views (ui.py and api.py) should go through
these functions.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import db
from app.models import Person


def get_people(sort: str = "name", status: str = "active") -> list[Person]:
    # Start the base SELECT statement
    query = db.select(Person)

    # Apply sorting
    if sort == "name":
        query = query.order_by(Person.name)
    elif sort == "location":
        query = query.order_by(Person.location)
    elif sort == "updated":
        query = query.order_by(Person.updated_at.desc())

    # Apply filter based on status
    if status == "active":
        query = query.where(Person.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Person.archived_at.is_not(None))
    # No filter if status == "all"

    try:
        return list(db.session.execute(query).scalars().all())
    except SQLAlchemyError:
        try:
            db.session.rollback()
        except Exception:
            pass
        raise


def get_person(id: UUID) -> Person:
    return db.get_or_404(Person, id)


def create_person(
    name: str,
    email_address: str,
    location: str,
    role_id: UUID,
    team_id: UUID | None,
    manager_id: UUID | None,
) -> Person:
    person: Person = Person(
        name=name.title(),
        email_address=email_address.lower(),
        location=location,
        role_id=role_id,
        team_id=team_id,
        manager_id=manager_id,
    )
    # Add the new person instance to the session
    db.session.add(person)
    try:
        # Attempt to commit the transaction to persist the person
        db.session.commit()
        return person
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise


def update_person(
    id: UUID,
    name: str,
    email_address: str,
    location: str,
    role_id: UUID,
    team_id: UUID | None,
    manager_id: UUID | None,
) -> None:
    # Retrieve the person or raise 404 if not found
    person = db.get_or_404(Person, id)
    # Update the person's attributes with the new values
    person.name = name.title()
    person.email_address = email_address.lower()
    person.location = location
    person.role_id = role_id
    person.team_id = team_id
    person.manager_id = manager_id
    try:
        # Commit the update transaction
        db.session.commit()
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise


def archive_person(id: UUID) -> None:
    # Retrieve the person or raise 404 if not found
    person = db.get_or_404(Person, id)
    # Set the archived_at timestamp to mark the person as archived
    person.archived_at = datetime.now(timezone.utc)
    try:
        # Commit the archive action
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def restore_person(id: UUID) -> None:
    # Retrieve the person or raise 404 if not found
    person = db.get_or_404(Person, id)
    # Clear the archived_at timestamp to mark the person as active
    person.archived_at = None
    try:
        # Commit the restore action
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def download_people() -> list[Person]:
    try:
        return list(
            db.session.execute(
                db.select(Person)
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
        try:
            db.session.rollback()
        except Exception:
            pass
        raise
