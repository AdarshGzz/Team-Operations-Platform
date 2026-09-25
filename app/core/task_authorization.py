from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db_session
from app.models.task import Task
from app.models.team_member import TeamMember
from app.models.user import User, UserRole


async def require_team_task_access(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Verify that the current user can access resources
    belonging to the requested team.
    ADMIN:
        Can access any team.
    MANAGER:
        Can access teams they belong to.
    MEMBER:
        Can access teams they belong to.
    """
    if current_user.role == UserRole.ADMIN:
        return current_user
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this team",
        )
    return current_user


async def require_task_view_access(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Verify that the current user can view a task.
    ADMIN:
        Can view any task.
    MANAGER:
        Can view tasks belonging to their teams.
    MEMBER:
        Can view tasks belonging to their teams.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.role == UserRole.ADMIN:
        return current_user
    membership_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == task.team_id,
            TeamMember.user_id == current_user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task",
        )
    return current_user


async def require_task_manage_access(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Verify that the current user can modify a task.
    ADMIN:
        Can modify any task.
    MANAGER:
        Can modify tasks belonging to their teams.
    MEMBER:
        Can modify only tasks assigned to them.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if current_user.role == UserRole.ADMIN:
        return current_user
    if current_user.role == UserRole.MANAGER:
        membership_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == task.team_id,
                TeamMember.user_id == current_user.id,
            )
        )
        if membership_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not manage this team's tasks",
            )
        return current_user
    if task.assignee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify tasks assigned to you",
        )
    return current_user
