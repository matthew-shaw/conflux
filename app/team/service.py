"""Team service module providing data access and business logic operations.

This module contains functions for CRUD operations on Team objects, handling
database interactions, transaction management, and query construction. All
database access from the team views (ui.py and api.py) should go through
these functions.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from app import db
from app.models import Team

logger = logging.getLogger(__name__)


def get_teams(sort: str = "name", status: str = "active") -> list[Team]:
    """Retrieve a list of teams with optional sorting and filtering.

    Args:
        sort: Sort order for results. Valid values are "name" or
            "updated". Defaults to "name".
        status: Filter by archive status. Valid values are "active" (non-archived),
            "archived" (archived only), or "all" (no filter). Defaults to "active".

    Returns:
        A list of Team objects matching the specified criteria, sorted as requested.

    Example:
        >>> active_teams = get_teams()  # Get active teams sorted by name
        >>> archived_teams = get_teams(sort="updated", status="archived")
    """
    # Start the base SELECT statement
    query = db.select(Team)

    # Apply sorting based on the sort parameter
    if sort == "name":
        query = query.order_by(Team.name)
    elif sort == "updated":
        # Sort by most recently updated first
        query = query.order_by(Team.updated_at.desc())

    # Apply filter based on status parameter
    if status == "active":
        # Only return non-archived teams
        query = query.where(Team.archived_at.is_(None))
    elif status == "archived":
        # Only return archived teams
        query = query.where(Team.archived_at.is_not(None))
    # If status == "all", no filter is applied

    try:
        return list(db.session.execute(query).scalars().all())
    except SQLAlchemyError:
        # defensive rollback and bubble up for handlers to translate to HTTP responses
        db.session.rollback()
        logger.debug(
            f"Database error retrieving teams (sort={sort},status={status})",
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


def create_team(name: str) -> Team:
    """Create a new team in the database.

    Args:
        name: The name of the new team. Must be unique.

    Returns:
        The newly created Team object with all database-assigned fields populated.

    Raises:
        sqlalchemy.exc.IntegrityError: If a team with the same name already exists,
            indicating a uniqueness constraint violation.

    Example:
        >>> team = create_team(name="Senior Manager")
    """
    team = Team(name=name)
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


def update_team(id: UUID, name: str) -> None:
    """Update an existing team's name.

    Args:
        id: The UUID of the team to update.
        name: The new name for the team. Must remain unique.

    Raises:
        werkzeug.exceptions.NotFound: If no team with the given ID exists.
        sqlalchemy.exc.IntegrityError: If the new name violates the uniqueness
            constraint (i.e., another team already has that name).

    Example:
        >>> team = update_team(team_id, "Senior Manager", "G7")
    """
    # Retrieve the team or raise 404 if not found
    team = get_team(id)
    # Update the team's name
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
    """Archive an existing team by setting its archived_at timestamp.

    Archived teams are effectively soft-deleted and can be restored later.
    The timestamp is set to the current UTC time.

    Args:
        id: The UUID of the team to archive.

    Raises:
        werkzeug.exceptions.NotFound: If no team with the given ID exists.

    Example:
        >>> team = archive_team(team_id)
    """
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
    """Restore a previously archived team.

    Restoring a team clears its archived_at timestamp, making it active again.

    Args:
        id: The UUID of the team to restore.

    Raises:
        werkzeug.exceptions.NotFound: If no team with the given ID exists.

    Example:
        >>> team = restore_team(team_id)
    """
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
