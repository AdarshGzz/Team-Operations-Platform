from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
