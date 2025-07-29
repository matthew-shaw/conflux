import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import TIMESTAMP, ForeignKey, Table, func
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
        ForeignKey("services.id"),
        primary_key=True,
        index=True,
    ),
    db.Column(
        "component_id",
        UUID(as_uuid=True),
        ForeignKey("components.id"),
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
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    people: Mapped[List["Person"]] = relationship("Person", back_populates="role")


class Team(db.Model):  # noqa: F811
    """
    Represents a team to which people belong and which owns services.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    people: Mapped[List["Person"]] = relationship("Person", back_populates="team")
    services: Mapped[List["Service"]] = relationship("Service", back_populates="team")


class Person(db.Model):  # noqa: F811
    """
    Represents a person who belongs to a team and performs a role.
    """

    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    role: Mapped["Role"] = relationship("Role", back_populates="people")
    team: Mapped["Team"] = relationship("Team", back_populates="people")


class Service(db.Model):  # noqa: F811
    """
    Represents a service owned by a team and composed of components.
    """

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    team: Mapped["Team"] = relationship("Team", back_populates="services")
    components: Mapped[List["Component"]] = relationship(
        "Component", secondary=service_components, back_populates="services"
    )


class Component(db.Model):  # noqa: F811
    """
    Represents a component that can be used by multiple services.
    """

    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    services: Mapped[List["Service"]] = relationship(
        "Service", secondary=service_components, back_populates="components"
    )
