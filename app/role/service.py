"""Role service module providing data access and business logic operations.

This module contains functions for CRUD operations on Role objects, handling
database interactions, transaction management, and query construction. All
database access from the role views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app import db
from app.exceptions import ArchivedEntityError
from app.models import Role

logger = logging.getLogger(__name__)


def get_roles(
    sort: str = "name",
    status: str = "active",
    page: int = 1,
    per_page: int = 25,
) -> Pagination:
    """Retrieve a paginated list of roles."""

    # Start the base SELECT statement
    query = db.select(Role)

    # Apply sorting
    if sort == "name":
        query = query.order_by(Role.name)
    elif sort == "grade":
        query = query.order_by(Role.grade)
    elif sort == "updated":
        query = query.order_by(Role.updated_at.desc())

    # Apply filter based on status
    if status == "active":
        query = query.where(Role.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Role.archived_at.is_not(None))
    # No filter if status == "all"

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
            f"Database error retrieving roles (sort={sort}, status={status}, page={page}, per_page={per_page})",
            exc_info=True,
        )
        raise


def get_active_roles() -> list[Role]:
    """Retrieve a list of all roles without pagination."""
    try:
        return list(
            db.session.execute(db.select(Role).order_by(Role.name).where(Role.archived_at.is_(None))).scalars().all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error retrieving all roles", exc_info=True)
        raise


def get_role(id: UUID) -> Role:
    try:
        return db.session.execute(db.select(Role).filter_by(id=id)).scalar_one()
    except NoResultFound:
        logger.debug(f"Role not found {id}", exc_info=True)
        raise


def create_role(
    name: str,
    grade: str,
) -> Role:
    role: Role = Role(
        name=name,
        grade=grade,
    )
    # Add the new role instance to the session
    db.session.add(role)
    logger.info(f"Creating role: {name}")
    try:
        # Attempt to commit the transaction to persist the role
        db.session.commit()
        logger.info(f"Created role: {name} (id={getattr(role, 'id', None)})")
        return role
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        logger.debug(f"IntegrityError creating role {name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error creating role {name}", exc_info=True)
        raise


def update_role(
    id: UUID,
    name: str,
    grade: str,
) -> None:
    # Retrieve the role or raise 404 if not found
    role = get_role(id)
    # Prevent editing archived roles
    if role.archived_at is not None:
        raise ArchivedEntityError(f"Cannot update archived role {id}")
    # Update the role's attributes with the new values
    role.name = name
    role.grade = grade
    logger.info(f"Updating role {id} -> name={name}")
    try:
        # Commit the update transaction
        db.session.commit()
        logger.info(f"Updated role {id}")
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        logger.debug(f"IntegrityError updating role {id} to name={name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error updating role {id}", exc_info=True)
        raise


def archive_role(id: UUID) -> None:
    # Retrieve the role or raise 404 if not found
    role = get_role(id)
    # Set the archived_at timestamp to mark the role as archived
    role.archived_at = datetime.now(timezone.utc)
    logger.info(f"Archiving role {id}")
    try:
        # Commit the archive action
        db.session.commit()
        logger.info(f"Archived role {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error archiving role {id}", exc_info=True)
        raise


def restore_role(id: UUID) -> None:
    # Retrieve the role or raise 404 if not found
    role = get_role(id)
    # Clear the archived_at timestamp to mark the role as active
    role.archived_at = None
    logger.info(f"Restoring role {id}")
    try:
        # Commit the restore action
        db.session.commit()
        logger.info(f"Restored role {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error restoring role {id}", exc_info=True)
        raise


def download_roles() -> list[Role]:
    try:
        return list(db.session.execute(db.select(Role).order_by(Role.name)).scalars().all())
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error downloading roles", exc_info=True)
        raise
