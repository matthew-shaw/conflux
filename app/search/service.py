"""Search service module providing query operations across domains."""

import logging

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Person, Role, Service, Team

logger = logging.getLogger(__name__)


def search_entries(query: str) -> list[dict[str, object]]:
    """Search across all domains and return mixed results for the search page."""
    try:
        search_pattern = f"%{query.strip()}%"

        roles = (
            db.session.execute(
                db.select(Role).filter(
                    or_(
                        Role.name.ilike(search_pattern),
                        Role.grade.ilike(search_pattern),
                    )
                )
            )
            .scalars()
            .all()
        )
        people = (
            db.session.execute(
                db.select(Person).filter(
                    or_(
                        Person.name.ilike(search_pattern),
                        Person.location.ilike(search_pattern),
                    )
                )
            )
            .scalars()
            .all()
        )
        teams = db.session.execute(db.select(Team).filter(Team.name.ilike(search_pattern))).scalars().all()
        services = db.session.execute(db.select(Service).filter(Service.name.ilike(search_pattern))).scalars().all()

        results: list[dict[str, object]] = []
        for role in roles:
            results.append(
                {
                    "type": "Role",
                    "id": role.id,
                    "name": role.name,
                    "updated_at": role.updated_at,
                    "url": None,
                }
            )
        for person in people:
            results.append(
                {
                    "type": "Person",
                    "id": person.id,
                    "name": person.name,
                    "updated_at": person.updated_at,
                    "url": None,
                }
            )
        for team in teams:
            results.append(
                {
                    "type": "Team",
                    "id": team.id,
                    "name": team.name,
                    "updated_at": team.updated_at,
                    "url": None,
                }
            )
        for service in services:
            results.append(
                {
                    "type": "Service",
                    "id": service.id,
                    "name": service.name,
                    "updated_at": service.updated_at,
                    "url": None,
                }
            )

        results.sort(key=lambda result: str(result["name"]).lower())
        return results
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Database error searching for {query}", exc_info=True)
        raise
