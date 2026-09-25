from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.task import TaskStatus
from app.models.task_event import TaskEvent, TaskEventType
from app.services.task_scheduler import process_overdue_tasks


@pytest.mark.asyncio
async def test_due_task_becomes_overdue(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.TODO

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 1

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE


@pytest.mark.asyncio
async def test_in_progress_task_becomes_overdue(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.IN_PROGRESS

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 1

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE


@pytest.mark.asyncio
async def test_overdue_task_creates_event(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.TODO

    await db_session.commit()

    await process_overdue_tasks(
        db_session,
    )

    result = await db_session.execute(
        select(TaskEvent).where(
            TaskEvent.task_id == task.id,
            TaskEvent.event_type == TaskEventType.OVERDUE,
        )
    )

    event = result.scalar_one_or_none()

    assert event is not None
    assert event.payload is not None
    assert event.payload["due_at"] is not None


@pytest.mark.asyncio
async def test_future_task_does_not_become_overdue(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) + timedelta(hours=1)
    task.status = TaskStatus.TODO

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 0

    await db_session.refresh(task)

    assert task.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_completed_task_does_not_become_overdue(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.COMPLETED

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 0

    await db_session.refresh(task)

    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_cancelled_task_does_not_become_overdue(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.CANCELLED

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 0

    await db_session.refresh(task)

    assert task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_already_overdue_task_is_not_processed_again(
    db_session,
    task,
):
    task.due_at = datetime.now(UTC) - timedelta(minutes=5)
    task.status = TaskStatus.OVERDUE

    await db_session.commit()

    updated_count = await process_overdue_tasks(
        db_session,
    )

    assert updated_count == 0

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE
