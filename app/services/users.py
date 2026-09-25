from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserService:
    def list_users(
        self,
        db: Session,
    ) -> list[User]:
        result = db.execute(select(User).order_by(User.created_at.desc()))

        return list(result.scalars().all())

    def get_user(
        self,
        db: Session,
        *,
        user_id: UUID,
    ) -> User | None:
        result = db.execute(select(User).where(User.id == user_id))

        return result.scalar_one_or_none()

    def update_user(
        self,
        db: Session,
        *,
        user: User,
        role: UserRole | None,
        is_active: bool | None,
    ) -> User:
        if role is not None:
            user.role = role

        if is_active is not None:
            user.is_active = is_active

        db.commit()
        db.refresh(user)

        return user


user_service = UserService()
