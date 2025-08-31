import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db

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
    grade: Mapped[str] = mapped_column(nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    people: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="role",
        cascade="save-update",
        passive_deletes=True,
        order_by="Person.name",
    )

    def to_dict(self, include_people: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "name": self.name,
            "grade": self.grade,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        if include_people:
            data["people"] = [person.to_dict(include_team=True) for person in self.people]
        return data


class Team(db.Model):  # noqa: F811
    """
    Represents a team to which people belong and which owns services.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    people: Mapped[List["Person"]] = relationship(
        "Person",
        back_populates="team",
        cascade="save-update",
        passive_deletes=True,
        order_by="Person.name",
    )
    services: Mapped[List["Service"]] = relationship(
        "Service",
        back_populates="team",
        cascade="save-update",
        passive_deletes=True,
        order_by="Service.name",
    )

    def to_dict(self, include_people: bool = False, include_services: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "name": self.name,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        if include_people:
            data["people"] = [person.to_dict(include_role=True) for person in self.people]
        if include_services:
            data["services"] = [service.to_dict() for service in self.services]
        return data


class Person(db.Model):  # noqa: F811
    """
    Represents a person who belongs to a team and performs a role.
    """

    __tablename__ = "people"

    # Attributes
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    location: Mapped[str] = mapped_column(nullable=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign Keys
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="people", passive_deletes=True)
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="people", passive_deletes=True)
    manager: Mapped[Optional["Person"]] = relationship(
        "Person",
        remote_side=[id],
        back_populates="reports",
        foreign_keys=[manager_id],
        passive_deletes=True,
    )
    reports: Mapped[list["Person"]] = relationship(
        "Person",
        back_populates="manager",
        cascade="save-update",
        passive_deletes=True,
        order_by="Person.name",
    )

    def to_dict(
        self,
        include_role: bool = False,
        include_team: bool = False,
        include_manager: bool = False,
        include_reports: bool = False,
    ) -> dict:
        data = {
            "id": str(self.id),
            "name": self.name,
            "location": self.location,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        if include_role and self.role:
            data["role"] = self.role.to_dict()
        if include_team and self.team:
            data["team"] = self.team.to_dict()
        if include_manager and self.manager:
            data["manager"] = self.manager.to_dict(include_role=True, include_team=True)
        if include_reports:
            data["reports"] = [report.to_dict(include_role=True, include_team=True) for report in self.reports]
        return data


class Service(db.Model):  # noqa: F811
    """
    Represents a service owned by a team and composed of components.
    """

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
        order_by="Component.name",
    )

    def to_dict(self, include_team: bool = False, include_components: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "name": self.name,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        if include_team and self.team:
            data["team"] = self.team.to_dict()
        if include_components:
            data["components"] = [component.to_dict() for component in self.components]
        return data


class Component(db.Model):  # noqa: F811
    """
    Represents a component that can be used by multiple services.
    """

    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    services: Mapped[List["Service"]] = relationship(
        "Service",
        secondary=service_components,
        back_populates="components",
        passive_deletes=True,
        order_by="Service.name",
    )

    def to_dict(self, include_services: bool = False) -> dict:
        data = {
            "id": str(self.id),
            "name": self.name,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        if include_services:
            data["services"] = [service.to_dict() for service in self.services]
        return data
