"""Service service module providing data access and business logic operations.

This module contains functions for CRUD operations on Service objects, handling
database interactions, transaction management, and query construction. All
database access from the service views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import db
from app.exceptions import ArchivedEntityError
from app.models import Service

logger = logging.getLogger(__name__)


def get_services(
    sort: str = "name",
    status: str = "active",
    page: int = 1,
    per_page: int = 25,
) -> Pagination:
    """Retrieve a paginated list of services."""

    # Start the base SELECT statement
    query = db.select(Service)

    # Apply sorting
    if sort == "name":
        query = query.order_by(Service.name)
    elif sort == "updated":
        query = query.order_by(Service.updated_at.desc())

    # Apply filter based on status
    if status == "active":
        query = query.where(Service.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Service.archived_at.is_not(None))
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
            f"Database error retrieving services (sort={sort}, status={status}, page={page}, per_page={per_page})",
            exc_info=True,
        )
        raise


def get_active_services() -> list[Service]:
    """Retrieve a list of all services without pagination."""
    try:
        return list(
            db.session.execute(db.select(Service).order_by(Service.name).where(Service.archived_at.is_(None)))
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error retrieving all services", exc_info=True)
        raise


def get_service(id: UUID) -> Service:
    try:
        return db.session.execute(db.select(Service).filter_by(id=id)).scalar_one()
    except NoResultFound:
        logger.debug(f"Service not found {id}", exc_info=True)
        raise


def create_service(
    name: str,
    description: str,
    team_id: UUID | None,
) -> Service:
    service: Service = Service(
        name=name.title(),
        description=description,
        team_id=team_id,
    )
    # Add the new service instance to the session
    db.session.add(service)
    logger.info(f"Creating service: {name}")
    try:
        # Attempt to commit the transaction to persist the service
        db.session.commit()
        logger.info(f"Created service: {name} (id={getattr(service, 'id', None)})")
        return service
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        logger.debug(f"IntegrityError creating service {name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error creating service {name}", exc_info=True)
        raise


def update_service(
    id: UUID,
    name: str,
    description: str,
    team_id: UUID | None,
) -> None:
    # Retrieve the service or raise 404 if not found
    service = get_service(id)
    # Prevent editing archived services
    if service.archived_at is not None:
        raise ArchivedEntityError(f"Cannot update archived service {id}")
    # Update the service's attributes with the new values
    service.name = name.title()
    service.description = description
    service.team_id = team_id
    logger.info(f"Updating service {id} -> name={name}")
    try:
        # Commit the update transaction
        db.session.commit()
        logger.info(f"Updated service {id}")
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        logger.debug(f"IntegrityError updating service {id} to name={name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error updating service {id}", exc_info=True)
        raise


def archive_service(id: UUID) -> None:
    # Retrieve the service or raise 404 if not found
    service = get_service(id)
    # Set the archived_at timestamp to mark the service as archived
    service.archived_at = datetime.now(timezone.utc)
    logger.info(f"Archiving service {id}")
    try:
        # Commit the archive action
        db.session.commit()
        logger.info(f"Archived service {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error archiving service {id}", exc_info=True)
        raise


def restore_service(id: UUID) -> None:
    # Retrieve the service or raise 404 if not found
    service = get_service(id)
    # Clear the archived_at timestamp to mark the service as active
    service.archived_at = None
    logger.info(f"Restoring service {id}")
    try:
        # Commit the restore action
        db.session.commit()
        logger.info(f"Restored service {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error restoring service {id}", exc_info=True)
        raise


def download_services() -> list[Service]:
    try:
        return list(
            db.session.execute(
                db.select(Service)
                .options(
                    selectinload(Service.team),
                )
                .order_by(Service.name)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error downloading services", exc_info=True)
        raise
