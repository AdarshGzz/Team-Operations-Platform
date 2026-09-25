import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class TaskEventType(enum.StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    OVERDUE = "OVERDUE"
    COMPLETED = "COMPLETED"


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    task_id = Column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type = Column(
        Enum(TaskEventType, name="task_event_type"),
        nullable=False,
    )

    payload = Column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task = relationship(
        "Task",
        back_populates="events",
    )

    __table_args__ = (
        Index(
            "ix_task_events_task_event_type",
            "task_id",
            "event_type",
        ),
    )
