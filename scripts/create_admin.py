from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def create_admin() -> None:
    email = input("Admin email: ").strip().lower()
    name = input("Admin name: ").strip()
    password = input("Admin password: ")

    with SessionLocal() as db:
        result = db.execute(select(User).where(User.email == email))

        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.role == UserRole.ADMIN:
                print("User is already an admin.")
                return

            existing_user.role = UserRole.ADMIN
            db.commit()

            print("Existing user promoted to admin.")
            return

        admin = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("Admin user created.")


if __name__ == "__main__":
    create_admin()
