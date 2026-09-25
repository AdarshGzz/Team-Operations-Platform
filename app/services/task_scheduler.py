import threading
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType

OVERDUE_CHECK_INTERVAL_SECONDS = 300

_stop_event = threading.Event()
_scheduler_thread: threading.Thread | None = None


def process_overdue_tasks(
    db: Session | None = None,
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
        with SessionLocal() as session:
            return _mark_overdue_tasks(session)

    return _mark_overdue_tasks(db)


def _mark_overdue_tasks(db: Session) -> int:
    now = datetime.now(UTC)

    result = db.execute(
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

    db.commit()

    return len(tasks)


def overdue_task_scheduler() -> None:
    """
    Continuously check for overdue tasks.

    The scheduler runs independently from API request handling.
    """

    while not _stop_event.is_set():
        try:
            process_overdue_tasks()

        except Exception:
            pass

        _stop_event.wait(OVERDUE_CHECK_INTERVAL_SECONDS)


def start_overdue_task_scheduler() -> None:
    """
    Start the overdue task scheduler on a background thread.
    """

    global _scheduler_thread

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return

    _stop_event.clear()

    _scheduler_thread = threading.Thread(
        target=overdue_task_scheduler,
        name="overdue-task-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()


def stop_overdue_task_scheduler() -> None:
    """
    Signal the overdue task scheduler to stop and wait for it.
    """

    global _scheduler_thread

    _stop_event.set()

    if _scheduler_thread is not None:
        _scheduler_thread.join()
        _scheduler_thread = None
