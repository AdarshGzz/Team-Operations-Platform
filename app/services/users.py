from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserService:
    async def list_users(
        self,
        db: AsyncSession,
    ) -> list[User]:
        result = await db.execute(select(User).order_by(User.created_at.desc()))

        return list(result.scalars().all())

    async def get_user(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
    ) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))

        return result.scalar_one_or_none()

    async def update_user(
        self,
        db: AsyncSession,
        *,
        user: User,
        role: UserRole | None,
        is_active: bool | None,
    ) -> User:
        if role is not None:
            user.role = role

        if is_active is not None:
            user.is_active = is_active

        await db.commit()
        await db.refresh(user)

        return user


user_service = UserService()
