"""Main service module providing dashboard query helpers."""

import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Person, Role, Service, Team

logger = logging.getLogger(__name__)


def get_dashboard_counts() -> dict[str, int]:
    """Return active counts for the application dashboard."""
    try:
        return {
            "roles": db.session.scalar(db.select(func.count()).select_from(Role).where(Role.archived_at.is_(None)))
            or 0,
            "teams": db.session.scalar(db.select(func.count()).select_from(Team).where(Team.archived_at.is_(None)))
            or 0,
            "people": db.session.scalar(db.select(func.count()).select_from(Person).where(Person.archived_at.is_(None)))
            or 0,
            "services": db.session.scalar(
                db.select(func.count()).select_from(Service).where(Service.archived_at.is_(None))
            )
            or 0,
        }
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug("Database error retrieving dashboard counts", exc_info=True)
        raise
