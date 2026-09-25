from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole


class AuthService:
    def register(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        name: str,
    ) -> User:
        result = db.execute(select(User).where(User.email == email))

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
        db.commit()
        db.refresh(user)

        return user

    def authenticate(
        self,
        db: Session,
        *,
        email: str,
        password: str,
    ) -> str | None:
        result = db.execute(select(User).where(User.email == email))

        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return create_access_token(str(user.id))


auth_service = AuthService()
