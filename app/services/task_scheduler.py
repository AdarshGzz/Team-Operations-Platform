import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.task import Task, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType

logger = logging.getLogger(__name__)


OVERDUE_CHECK_INTERVAL_SECONDS = 300


async def process_overdue_tasks(
    db: AsyncSession | None = None,
) -> int:
    """
    Find active tasks whose due date has passed and mark them
    as OVERDUE.

    When no session is provided, a dedicated session is opened
    (this is how the background scheduler calls it). Tests inject
    their own session so the work stays inside the test transaction.

    Returns the number of tasks updated.
    """

    if db is None:
        async with AsyncSessionLocal() as session:
            return await _mark_overdue_tasks(session)

    return await _mark_overdue_tasks(db)


async def _mark_overdue_tasks(db: AsyncSession) -> int:
    now = datetime.now(UTC)

    result = await db.execute(
        select(Task).where(
            Task.due_at.is_not(None),
            Task.due_at < now,
            Task.status.in_(
                [
                    TaskStatus.TODO,
                    TaskStatus.IN_PROGRESS,
                ]
            ),
        )
    )

    tasks = list(result.scalars().all())

    if not tasks:
        return 0

    for task in tasks:
        task.status = TaskStatus.OVERDUE

        db.add(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.OVERDUE,
                payload={
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                },
            )
        )

    await db.commit()

    return len(tasks)


async def overdue_task_scheduler() -> None:
    """
    Continuously check for overdue tasks.

    The scheduler runs independently from API request handling.
    """

    logger.info("Overdue task scheduler started")

    while True:
        try:
            updated_count = await process_overdue_tasks()

            if updated_count:
                logger.info(
                    "Marked %d task(s) as overdue",
                    updated_count,
                )

        except asyncio.CancelledError:
            logger.info("Overdue task scheduler stopped")
            raise

        except Exception:
            logger.exception("Error while processing overdue tasks")

        await asyncio.sleep(OVERDUE_CHECK_INTERVAL_SECONDS)
