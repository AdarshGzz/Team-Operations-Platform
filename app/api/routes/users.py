from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.authorization import require_roles
from app.core.database import get_db_session
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.users import user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserResponse],
)
async def list_users(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN),
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    users = await user_service.list_users(db)

    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN),
    ),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await user_service.get_user(
        db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN),
    ),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await user_service.get_user(
        db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id and request.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    user = await user_service.update_user(
        db,
        user=user,
        role=request.role,
        is_active=request.is_active,
    )

    return UserResponse.model_validate(user)
