from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus
from app.models.task_event import TaskEventType


class TaskCreateRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    priority: TaskPriority = TaskPriority.MEDIUM

    assignee_id: UUID | None = None

    due_at: datetime | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    priority: TaskPriority | None = None

    assignee_id: UUID | None = None

    due_at: datetime | None = None


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    title: str
    description: str | None

    team_id: UUID
    created_by: UUID
    assignee_id: UUID | None

    status: TaskStatus
    priority: TaskPriority

    due_at: datetime | None
    completed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class TaskEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    task_id: UUID
    event_type: TaskEventType
    payload: dict | None
    created_at: datetime
