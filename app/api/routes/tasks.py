from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_roles
from app.core.database import get_db_session
from app.core.task_authorization import (
    require_task_manage_access,
    require_task_view_access,
    require_team_task_access,
)
from app.models.user import User, UserRole
from app.schemas.task import (
    TaskCreateRequest,
    TaskEventResponse,
    TaskResponse,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)
from app.services.task import task_service

router = APIRouter(
    tags=["Tasks"],
)


@router.post(
    "/teams/{team_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    team_id: UUID,
    request: TaskCreateRequest,
    current_user: User = Depends(
        require_team_task_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    try:
        task = await task_service.create_task(
            db,
            team_id=team_id,
            created_by=current_user.id,
            title=request.title,
            description=request.description,
            priority=request.priority,
            assignee_id=request.assignee_id,
            due_at=request.due_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return TaskResponse.model_validate(task)


@router.get(
    "/teams/{team_id}/tasks",
    response_model=list[TaskResponse],
)
async def list_team_tasks(
    team_id: UUID,
    current_user: User = Depends(
        require_team_task_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[TaskResponse]:
    tasks = await task_service.list_team_tasks(
        db,
        team_id=team_id,
    )
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(
        require_task_view_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    task = await task_service.get_task(
        db,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskResponse.model_validate(task)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: UUID,
    request: TaskUpdateRequest,
    current_user: User = Depends(
        require_task_manage_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    task = await task_service.get_task(
        db,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    try:
        task = await task_service.update_task(
            db,
            task=task,
            title=request.title,
            description=request.description,
            priority=request.priority,
            assignee_id=request.assignee_id,
            due_at=request.due_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return TaskResponse.model_validate(task)


@router.patch(
    "/tasks/{task_id}/status",
    response_model=TaskResponse,
)
async def update_task_status(
    task_id: UUID,
    request: TaskStatusUpdateRequest,
    current_user: User = Depends(
        require_task_manage_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    task = await task_service.get_task(
        db,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    task = await task_service.update_status(
        db,
        task=task,
        status=request.status,
    )
    return TaskResponse.model_validate(task)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.MANAGER,
        ),
    ),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    task = await task_service.get_task(
        db,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.role == UserRole.MANAGER:
        # Managers can only delete tasks in their own teams.
        await require_team_task_access(
            team_id=task.team_id,
            current_user=current_user,
            db=db,
        )
    await task_service.delete_task(
        db,
        task=task,
    )


@router.get(
    "/tasks/{task_id}/events",
    response_model=list[TaskEventResponse],
)
async def list_task_events(
    task_id: UUID,
    current_user: User = Depends(
        require_task_view_access,
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[TaskEventResponse]:
    task = await task_service.get_task(
        db,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    events = await task_service.list_events(
        db,
        task_id=task_id,
    )
    return [TaskEventResponse.model_validate(event) for event in events]
