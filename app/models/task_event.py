import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.task import Task


class TaskEventType(enum.StrEnum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    OVERDUE = "OVERDUE"
    COMPLETED = "COMPLETED"


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[TaskEventType] = mapped_column(
        Enum(TaskEventType, name="task_event_type"),
        nullable=False,
    )

    payload: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task: Mapped["Task"] = relationship(
        back_populates="events",
    )

    __table_args__ = (
        Index(
            "ix_task_events_task_event_type",
            "task_id",
            "event_type",
        ),
    )
