import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db

if TYPE_CHECKING:
    # These imports are only for type checking to avoid runtime circular imports
    from app.models import Component, Person, Role, Service, Team

# Join table for services <-> components many-to-many relationship
service_components: Table = Table(
    "service_components",
    db.metadata,
    db.Column(
        "service_id",
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    db.Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Role(db.Model):  # noqa: F811
    """
    Represents a role that can be performed by a person.
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    people: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="role",
        cascade="save-update",
        passive_deletes=True,
    )


class Team(db.Model):  # noqa: F811
    """
    Represents a team to which people belong and which owns services.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    people: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="team",
        cascade="save-update",
        passive_deletes=True,
    )
    services: Mapped[List["Service"]] = relationship(
        "Service",
        back_populates="team",
        cascade="save-update",
        passive_deletes=True,
    )


class Person(db.Model):  # noqa: F811
    """
    Represents a person who belongs to a team and performs a role.
    """

    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    role: Mapped["Role"] = relationship("Role", back_populates="people", passive_deletes=True)
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="people", passive_deletes=True)


class Service(db.Model):  # noqa: F811
    """
    Represents a service owned by a team and composed of components.
    """

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="services", passive_deletes=True)
    components: Mapped[List["Component"]] = relationship(
        "Component",
        secondary=service_components,
        back_populates="services",
        passive_deletes=True,
    )


class Component(db.Model):  # noqa: F811
    """
    Represents a component that can be used by multiple services.
    """

    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    services: Mapped[List["Service"]] = relationship(
        "Service",
        secondary=service_components,
        back_populates="components",
        passive_deletes=True,
    )
