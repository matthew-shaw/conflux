"""Role service module providing data access and business logic operations.

This module contains functions for CRUD operations on Role objects, handling
database interactions, transaction management, and query construction. All
database access from the role views (ui.py and api.py) should go through
these functions.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Role


def get_roles(sort: str = "name", status: str = "active") -> list[Role]:
    """Retrieve a list of roles with optional sorting and filtering.

    Args:
        sort: Sort order for results. Valid values are "name", "grade", or
            "updated". Defaults to "name".
        status: Filter by archive status. Valid values are "active" (non-archived),
            "archived" (archived only), or "all" (no filter). Defaults to "active".

    Returns:
        A list of Role objects matching the specified criteria, sorted as requested.

    Example:
        >>> active_roles = get_roles()  # Get active roles sorted by name
        >>> archived_roles = get_roles(sort="updated", status="archived")
    """
    # Start the base SELECT statement
    query = db.select(Role)

    # Apply sorting based on the sort parameter
    if sort == "name":
        query = query.order_by(Role.name)
    elif sort == "grade":
        query = query.order_by(Role.grade)
    elif sort == "updated":
        # Sort by most recently updated first
        query = query.order_by(Role.updated_at.desc())

    # Apply filter based on status parameter
    if status == "active":
        # Only return non-archived roles
        query = query.where(Role.archived_at.is_(None))
    elif status == "archived":
        # Only return archived roles
        query = query.where(Role.archived_at.is_not(None))
    # If status == "all", no filter is applied

    return list(db.session.execute(query).scalars().all())


def get_role(id: UUID) -> Role:
    """Retrieve a single role by its ID.

    Args:
        id: The UUID of the role to retrieve.

    Returns:
        The Role object with the specified ID.

    Raises:
        werkzeug.exceptions.NotFound: If no role with the given ID exists.

    Example:
        >>> role = get_role(UUID('12345678-1234-5678-1234-567812345678'))
    """
    return db.get_or_404(Role, id)


def create_role(name: str, grade: str) -> Role:
    """Create a new role in the database.

    Args:
        name: The name of the new role. Must be unique.
        grade: The grade/level of the role.

    Returns:
        The newly created Role object with all database-assigned fields populated.

    Raises:
        sqlalchemy.exc.IntegrityError: If a role with the same name already exists,
            indicating a uniqueness constraint violation.

    Example:
        >>> role = create_role(name="Senior Manager", grade="Grade 7")
    """
    role = Role(name=name, grade=grade)
    # Add the new role instance to the session
    db.session.add(role)
    try:
        # Attempt to commit the transaction to persist the role
        db.session.commit()
        return role
    except IntegrityError:
        # Rollback on constraint violation (e.g., duplicate name)
        db.session.rollback()
        raise


def update_role(id: UUID, name: str) -> Role:
    """Update an existing role's name.

    Args:
        id: The UUID of the role to update.
        name: The new name for the role. Must remain unique.

    Returns:
        The updated Role object.

    Raises:
        werkzeug.exceptions.NotFound: If no role with the given ID exists.
        sqlalchemy.exc.IntegrityError: If the new name violates the uniqueness
            constraint (i.e., another role already has that name).

    Example:
        >>> role = update_role(role_id, "Senior Manager")
    """
    # Retrieve the role or raise 404 if not found
    role = db.get_or_404(Role, id)
    # Update the role's name
    role.name = name
    try:
        # Commit the update transaction
        db.session.commit()
        return role
    except IntegrityError:
        # Rollback if the new name violates uniqueness constraint
        db.session.rollback()
        raise


def archive_role(id: UUID) -> Role:
    """Archive an existing role by setting its archived_at timestamp.

    Archived roles are effectively soft-deleted and can be restored later.
    The timestamp is set to the current UTC time.

    Args:
        id: The UUID of the role to archive.

    Returns:
        The archived Role object with archived_at set to the current time.

    Raises:
        werkzeug.exceptions.NotFound: If no role with the given ID exists.

    Example:
        >>> role = archive_role(role_id)
    """
    # Retrieve the role or raise 404 if not found
    role = db.get_or_404(Role, id)
    # Set the archived_at timestamp to mark the role as archived
    role.archived_at = datetime.now(timezone.utc)
    # Commit the archive action
    db.session.commit()
    return role


def restore_role(id: UUID) -> Role:
    """Restore a previously archived role.

    Restoring a role clears its archived_at timestamp, making it active again.

    Args:
        id: The UUID of the role to restore.

    Returns:
        The restored Role object with archived_at set to None.

    Raises:
        werkzeug.exceptions.NotFound: If no role with the given ID exists.

    Example:
        >>> role = restore_role(role_id)
    """
    # Retrieve the role or raise 404 if not found
    role = db.get_or_404(Role, id)
    # Clear the archived_at timestamp to mark the role as active
    role.archived_at = None
    # Commit the restore action
    db.session.commit()
    return role
