import enum

from sqlalchemy import Boolean, Column, Enum, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(enum.StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    name = Column(
        String(100),
        nullable=False,
    )

    role = Column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.MEMBER,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    team_memberships = relationship(
        "TeamMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    created_tasks = relationship(
        "Task",
        foreign_keys="Task.created_by",
        back_populates="creator",
    )

    assigned_tasks = relationship(
        "Task",
        foreign_keys="Task.assignee_id",
        back_populates="assignee",
    )
