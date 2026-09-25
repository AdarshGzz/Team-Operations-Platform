from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType
from app.models.team_member import TeamMember
from app.models.user import User


class TaskService:
    def validate_assignee(
        self,
        db: Session,
        *,
        team_id: UUID,
        assignee_id: UUID,
    ) -> User:
        result = db.execute(
            select(User)
            .join(
                TeamMember,
                TeamMember.user_id == User.id,
            )
            .where(
                User.id == assignee_id,
                User.is_active.is_(True),
                TeamMember.team_id == team_id,
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("Assignee must be an active member of the team")

        return user

    def create_task(
        self,
        db: Session,
        *,
        team_id: UUID,
        created_by: UUID,
        title: str,
        description: str | None,
        priority: TaskPriority,
        assignee_id: UUID | None,
        due_at: datetime | None,
    ) -> Task:
        if assignee_id is not None:
            self.validate_assignee(
                db,
                team_id=team_id,
                assignee_id=assignee_id,
            )

        task = Task(
            team_id=team_id,
            created_by=created_by,
            title=title,
            description=description,
            priority=priority,
            assignee_id=assignee_id,
            due_at=due_at,
        )

        db.add(task)

        db.flush()

        db.add(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.CREATED,
                payload={
                    "title": title,
                    "priority": priority.value,
                },
            )
        )

        if assignee_id is not None:
            db.add(
                TaskEvent(
                    task_id=task.id,
                    event_type=TaskEventType.ASSIGNED,
                    payload={
                        "assignee_id": str(assignee_id),
                    },
                )
            )

        db.commit()
        db.refresh(task)

        return task

    def get_task(
        self,
        db: Session,
        *,
        task_id: UUID,
    ) -> Task | None:
        result = db.execute(
            select(Task).where(
                Task.id == task_id,
            )
        )

        return result.scalar_one_or_none()

    def list_team_tasks(
        self,
        db: Session,
        *,
        team_id: UUID,
    ) -> list[Task]:
        result = db.execute(
            select(Task).where(Task.team_id == team_id).order_by(Task.created_at.desc())
        )

        return list(result.scalars().all())

    def update_task(
        self,
        db: Session,
        *,
        task: Task,
        title: str | None,
        description: str | None,
        priority: TaskPriority | None,
        assignee_id: UUID | None,
        due_at: datetime | None,
    ) -> Task:
        old_assignee_id = task.assignee_id

        if assignee_id is not None and assignee_id != old_assignee_id:
            self.validate_assignee(
                db,
                team_id=task.team_id,
                assignee_id=assignee_id,
            )

        changed = False

        if title is not None and title != task.title:
            task.title = title
            changed = True

        if description is not None and description != task.description:
            task.description = description
            changed = True

        if priority is not None and priority != task.priority:
            task.priority = priority
            changed = True

        if assignee_id is not None and assignee_id != old_assignee_id:
            task.assignee_id = assignee_id
            changed = True

        if due_at is not None and due_at != task.due_at:
            task.due_at = due_at
            changed = True

        if not changed:
            return task

        db.add(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.UPDATED,
                payload={
                    "title": task.title,
                    "priority": task.priority.value,
                    "due_at": (task.due_at.isoformat() if task.due_at else None),
                },
            )
        )

        if assignee_id is not None and assignee_id != old_assignee_id:
            db.add(
                TaskEvent(
                    task_id=task.id,
                    event_type=TaskEventType.ASSIGNED,
                    payload={
                        "old_assignee_id": (
                            str(old_assignee_id) if old_assignee_id else None
                        ),
                        "new_assignee_id": str(assignee_id),
                    },
                )
            )

        db.commit()
        db.refresh(task)

        return task

    def update_status(
        self,
        db: Session,
        *,
        task: Task,
        status: TaskStatus,
    ) -> Task:
        old_status = task.status

        if old_status == status:
            return task

        task.status = status

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(UTC)
        else:
            task.completed_at = None

        event_type = TaskEventType.STATUS_CHANGED

        if status == TaskStatus.COMPLETED:
            event_type = TaskEventType.COMPLETED

        db.add(
            TaskEvent(
                task_id=task.id,
                event_type=event_type,
                payload={
                    "old_status": old_status.value,
                    "new_status": status.value,
                },
            )
        )

        db.commit()
        db.refresh(task)

        return task

    def delete_task(
        self,
        db: Session,
        *,
        task: Task,
    ) -> None:
        db.delete(task)
        db.commit()

    def list_events(
        self,
        db: Session,
        *,
        task_id: UUID,
    ) -> list[TaskEvent]:
        result = db.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.created_at.asc())
        )

        return list(result.scalars().all())


task_service = TaskService()
