"""Team service module providing data access and business logic operations.

This module contains functions for CRUD operations on Team objects, handling
database interactions, transaction management, and query construction. All
database access from the team views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app import db
from app.models import Team

logger = logging.getLogger(__name__)


def get_teams(
    sort: str = "name",
    status: str = "active",
    page: int = 1,
    per_page: int = 25,
) -> Pagination:
    """Retrieve a paginated list of teams."""

    # Start the base SELECT statement
    query = db.select(Team)

    # Apply sorting
    if sort == "name":
        query = query.order_by(Team.name)
    elif sort == "updated":
        query = query.order_by(Team.updated_at.desc())

    # Apply filter based on status
    if status == "active":
        query = query.where(Team.archived_at.is_(None))
    elif status == "archived":
        query = query.where(Team.archived_at.is_not(None))
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
            f"Database error retrieving teams (sort={sort}, status={status}, page={page}, per_page={per_page})",
            exc_info=True,
        )
        raise


def get_active_teams() -> list[Team]:
    """Retrieve a list of all teams without pagination."""
    try:
        return list(
            db.session.execute(db.select(Team).order_by(Team.name).where(Team.archived_at.is_(None))).scalars().all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error retrieving all teams", exc_info=True)
        raise


def get_team(id: UUID) -> Team:
    try:
        return db.session.execute(db.select(Team).filter_by(id=id)).scalar_one()
    except NoResultFound:
        logger.debug(f"Team not found {id}", exc_info=True)
        raise


def create_team(
    name: str,
) -> Team:
    team: Team = Team(
        name=name,
    )
    # Add the new team instance to the session
    db.session.add(team)
    logger.info(f"Creating team: {name}")
    try:
        # Attempt to commit the transaction to persist the team
        db.session.commit()
        logger.info(f"Created team: {name} (id={getattr(team, 'id', None)})")
        return team
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        logger.debug(f"IntegrityError creating team {name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error creating team {name}", exc_info=True)
        raise


def update_team(
    id: UUID,
    name: str,
) -> None:
    # Retrieve the team or raise 404 if not found
    team = get_team(id)
    # Update the team's attributes with the new values
    team.name = name
    logger.info(f"Updating team {id} -> name={name}")
    try:
        # Commit the update transaction
        db.session.commit()
        logger.info(f"Updated team {id}")
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        logger.debug(f"IntegrityError updating team {id} to name={name}", exc_info=True)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error updating team {id}", exc_info=True)
        raise


def archive_team(id: UUID) -> None:
    # Retrieve the team or raise 404 if not found
    team = get_team(id)
    # Set the archived_at timestamp to mark the team as archived
    team.archived_at = datetime.now(timezone.utc)
    logger.info(f"Archiving team {id}")
    try:
        # Commit the archive action
        db.session.commit()
        logger.info(f"Archived team {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error archiving team {id}", exc_info=True)
        raise


def restore_team(id: UUID) -> None:
    # Retrieve the team or raise 404 if not found
    team = get_team(id)
    # Clear the archived_at timestamp to mark the team as active
    team.archived_at = None
    logger.info(f"Restoring team {id}")
    try:
        # Commit the restore action
        db.session.commit()
        logger.info(f"Restored team {id}")
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error restoring team {id}", exc_info=True)
        raise


def download_teams() -> list[Team]:
    try:
        return list(db.session.execute(db.select(Team).order_by(Team.name)).scalars().all())
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error downloading teams", exc_info=True)
        raise
