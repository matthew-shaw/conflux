from uuid import UUID

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
