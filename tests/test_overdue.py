from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType
from app.services.task_scheduler import process_overdue_tasks


def _past() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=5)


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=5)


async def _overdue_events(
    db: AsyncSession,
    task_id,
) -> list[TaskEvent]:
    result = await db.execute(
        select(TaskEvent).where(
            TaskEvent.task_id == task_id,
            TaskEvent.event_type == TaskEventType.OVERDUE,
        )
    )

    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_due_task_is_marked_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.TODO

    await db_session.commit()

    updated_count = await process_overdue_tasks(db=db_session)

    assert updated_count >= 1

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE


@pytest.mark.asyncio
async def test_overdue_task_creates_event(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.TODO

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    events = await _overdue_events(db_session, task.id)

    assert len(events) == 1
    assert events[0].payload["due_at"] is not None


@pytest.mark.asyncio
async def test_in_progress_task_becomes_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.IN_PROGRESS

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE


@pytest.mark.asyncio
async def test_future_task_is_not_marked_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _future()
    task.status = TaskStatus.TODO

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.TODO
    assert await _overdue_events(db_session, task.id) == []


@pytest.mark.asyncio
async def test_task_without_due_date_is_not_marked_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = None
    task.status = TaskStatus.TODO

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.TODO
    assert await _overdue_events(db_session, task.id) == []


@pytest.mark.asyncio
async def test_completed_task_is_not_marked_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.COMPLETED

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.COMPLETED
    assert await _overdue_events(db_session, task.id) == []


@pytest.mark.asyncio
async def test_cancelled_task_is_not_marked_overdue(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.CANCELLED

    await db_session.commit()

    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.CANCELLED
    assert await _overdue_events(db_session, task.id) == []


@pytest.mark.asyncio
async def test_already_overdue_task_is_not_reprocessed(
    db_session: AsyncSession,
    task: Task,
):
    task.due_at = _past()
    task.status = TaskStatus.OVERDUE

    await db_session.commit()

    await process_overdue_tasks(db=db_session)
    await process_overdue_tasks(db=db_session)

    await db_session.refresh(task)

    assert task.status == TaskStatus.OVERDUE
    assert await _overdue_events(db_session, task.id) == []
