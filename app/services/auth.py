from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole


class AuthService:
    async def register(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        name: str,
    ) -> User:
        result = await db.execute(select(User).where(User.email == email))

        existing_user = result.scalar_one_or_none()

        if existing_user is not None:
            raise ValueError("A user with this email already exists")

        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=UserRole.MEMBER,
            is_active=True,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    async def authenticate(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> str | None:
        result = await db.execute(select(User).where(User.email == email))

        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return create_access_token(str(user.id))


auth_service = AuthService()
