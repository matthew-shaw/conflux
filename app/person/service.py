"""Person service module providing data access and business logic operations.

This module contains functions for CRUD operations on Person objects, handling
database interactions, transaction management, and query construction. All
database access from the person views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import db
from app.models import Person

logger = logging.getLogger(__name__)


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
        logger.debug(
            f"Database error retrieving people (sort={sort},status={status})",
            exc_info=True,
        )
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
    logger.info(f"Creating person: {name} email={email_address}")
    try:
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
    logger.info(f"Updating person {id} -> name={name} email={email_address}")
    try:
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
    # Retrieve the person or raise 404 if not found
    person = db.get_or_404(Person, id)
    # Set the archived_at timestamp to mark the person as archived
    person.archived_at = datetime.now(timezone.utc)
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
    # Retrieve the person or raise 404 if not found
    person = db.get_or_404(Person, id)
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
        logger.debug("Database error downloading people", exc_info=True)
        raise
