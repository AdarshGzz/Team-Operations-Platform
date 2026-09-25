from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.authorization import require_roles
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/admin-check",
)
async def admin_check(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN),
    ),
) -> dict[str, str]:

    return {
        "message": "Admin access granted",
        "user_id": str(current_user.id),
    }
