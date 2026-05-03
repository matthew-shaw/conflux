from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role


def get_roles(sort: str = "name", status: str = "active") -> list[Role]:
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

    return list(db.session.execute(query).scalars().all())


def get_role(id: UUID) -> Role:
    return db.get_or_404(Role, id)


def create_role(name: str, grade: str) -> Role:
    role = Role(name=name, grade=grade)
    db.session.add(role)
    try:
        db.session.commit()
        return role
    except IntegrityError:
        db.session.rollback()
        raise


def update_role(id: UUID, name: str) -> Role:
    role = db.get_or_404(Role, id)
    role.name = name
    try:
        db.session.commit()
        return role
    except IntegrityError:
        db.session.rollback()
        raise


def archive_role(id: UUID) -> Role:
    role = db.get_or_404(Role, id)
    role.archived_at = datetime.now(timezone.utc)
    db.session.commit()
    return role


def restore_role(id: UUID) -> Role:
    role = db.get_or_404(Role, id)
    role.archived_at = None
    db.session.commit()
    return role
