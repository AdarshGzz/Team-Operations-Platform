import os
from collections.abc import AsyncGenerator
from typing import Any

from app.core.security import hash_password
from app.models.user import User, UserRole

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_db_session
from app.main import app

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL environment variable is required to run tests."
    )


test_engine = create_async_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session")
async def database_connection() -> AsyncGenerator[AsyncConnection, None]:
    async with test_engine.connect() as connection:
        yield connection

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    database_connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession, None]:
    transaction = await database_connection.begin()

    session = AsyncSession(
        bind=database_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def register_user(client: AsyncClient):
    async def _register_user(
        *,
        email: str,
        password: str = "password123",
        name: str = "Test User",
    ) -> dict[str, Any]:
        response = await client.post(
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


@pytest_asyncio.fixture
async def login_user(client: AsyncClient):
    async def _login_user(
        *,
        email: str,
        password: str = "password123",
    ) -> str:
        response = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 200

        return response.json()["access_token"]

    return _login_user


@pytest_asyncio.fixture
async def auth_headers():
    def _auth_headers(token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
        }

    return _auth_headers


@pytest_asyncio.fixture
async def create_user(db_session: AsyncSession):

    async def _create_user(
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

        await db_session.flush()

        await db_session.refresh(user)

        return user

    return _create_user
