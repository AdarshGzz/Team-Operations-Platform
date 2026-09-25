import os
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db_session
from app.core.security import hash_password
from app.main import app
from app.models.task import Task
from app.models.user import User, UserRole

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL environment variable is required to run tests."
    )


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=Session,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def database_connection() -> Generator[Connection, None, None]:
    with test_engine.connect() as connection:
        yield connection

    test_engine.dispose()


@pytest.fixture
def db_session(
    database_connection: Connection,
) -> Generator[Session, None, None]:
    transaction = database_connection.begin()

    session = Session(
        bind=database_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()


@pytest.fixture
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    test_client = TestClient(app)

    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        test_client.close()


@pytest.fixture
def register_user(client: TestClient):
    def _register_user(
        *,
        email: str,
        password: str = "password123",
        name: str = "Test User",
    ) -> dict[str, Any]:
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name,
            },
        )

        assert response.status_code == 201

        return response.json()

    return _register_user


@pytest.fixture
def login_user(client: TestClient):
    def _login_user(
        *,
        email: str,
        password: str = "password123",
    ) -> str:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200

        return response.json()["access_token"]

    return _login_user


@pytest.fixture
def auth_headers():
    def _auth_headers(token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
        }

    return _auth_headers


@pytest.fixture
def create_user(db_session: Session):
    def _create_user(
        *,
        email: str,
        role: UserRole = UserRole.MEMBER,
        name: str = "Test User",
    ) -> User:
        user = User(
            email=email,
            password_hash=hash_password("password123"),
            name=name,
            role=role,
            is_active=True,
        )

        db_session.add(user)

        db_session.flush()

        db_session.refresh(user)

        return user

    return _create_user


@pytest.fixture
def team_context(
    client: TestClient,
    create_user,
    login_user,
    auth_headers,
) -> SimpleNamespace:
    """
    A team owned by an admin, with a manager and a member
    already added to it.
    """

    admin = create_user(
        email="lifecycle-admin@example.com",
        role=UserRole.ADMIN,
        name="Lifecycle Admin",
    )

    manager = create_user(
        email="lifecycle-manager@example.com",
        role=UserRole.MANAGER,
        name="Lifecycle Manager",
    )

    member = create_user(
        email="lifecycle-member@example.com",
        role=UserRole.MEMBER,
        name="Lifecycle Member",
    )

    outsider = create_user(
        email="lifecycle-outsider@example.com",
        role=UserRole.MEMBER,
        name="Lifecycle Outsider",
    )

    admin_token = login_user(email=admin.email)

    response = client.post(
        "/teams",
        json={
            "name": "Lifecycle Team",
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201

    team_id = response.json()["id"]

    for user in (manager, member):
        membership_response = client.post(
            f"/teams/{team_id}/members/{user.id}",
            headers=auth_headers(admin_token),
        )

        assert membership_response.status_code == 201

    return SimpleNamespace(
        admin=admin,
        manager=manager,
        member=member,
        outsider=outsider,
        team_id=team_id,
        admin_token=admin_token,
        manager_token=login_user(email=manager.email),
        member_token=login_user(email=member.email),
        outsider_token=login_user(email=outsider.email),
        auth_headers=auth_headers,
    )


@pytest.fixture
def manager_token(team_context: SimpleNamespace) -> str:
    return team_context.manager_token


@pytest.fixture
def admin_token(team_context: SimpleNamespace) -> str:
    return team_context.admin_token


@pytest.fixture
def member_token(team_context: SimpleNamespace) -> str:
    return team_context.member_token


@pytest.fixture
def admin_id(team_context: SimpleNamespace):
    return team_context.admin.id


@pytest.fixture
def member_id(team_context: SimpleNamespace):
    return team_context.member.id


@pytest.fixture
def manager_id(team_context: SimpleNamespace):
    return team_context.manager.id


@pytest.fixture
def team_id(team_context: SimpleNamespace) -> str:
    return team_context.team_id


@pytest.fixture
def outsider_token(team_context: SimpleNamespace) -> str:
    return team_context.outsider_token


@pytest.fixture
def task(
    client: TestClient,
    db_session: Session,
    team_context: SimpleNamespace,
) -> Task:
    """
    A task created by the team manager, returned as the ORM model
    so tests can inspect and mutate it directly.
    """

    response = client.post(
        f"/teams/{team_context.team_id}/tasks",
        json={
            "title": "Lifecycle Task",
        },
        headers=team_context.auth_headers(team_context.manager_token),
    )

    assert response.status_code == 201

    task_id = UUID(response.json()["id"])

    result = db_session.execute(
        select(Task).where(
            Task.id == task_id,
        )
    )

    return result.scalar_one()
