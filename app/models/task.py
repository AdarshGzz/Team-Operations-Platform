import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TaskStatus(enum.StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    OVERDUE = "OVERDUE"


class TaskPriority(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    team_id = Column(
        Uuid,
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_by = Column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    assignee_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.TODO,
    )

    priority = Column(
        Enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )

    due_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    team = relationship(
        "Team",
        back_populates="tasks",
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_tasks",
    )

    assignee = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )

    events = relationship(
        "TaskEvent",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tasks_team_status", "team_id", "status"),
        Index("ix_tasks_assignee_status", "assignee_id", "status"),
        Index("ix_tasks_due_at", "due_at"),
    )
