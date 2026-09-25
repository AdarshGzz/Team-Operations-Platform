import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "member@example.com",
            "password": "password123",
            "name": "Test Member",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "member@example.com"
    assert data["name"] == "Test Member"
    assert data["role"] == "MEMBER"
    assert data["is_active"] is True
    assert "id" in data
    # Password must never be returned by the API.
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "password123",
        "name": "First User",
    }
    first_response = await client.post(
        "/auth/register",
        json=payload,
    )
    assert first_response.status_code == 201
    second_response = await client.post(
        "/auth/register",
        json={
            **payload,
            "name": "Second User",
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == ("A user with this email already exists")


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "name": "Test User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "short@example.com",
            "password": "1234567",
            "name": "Test User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_name_required(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "email": "noname@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "name": "Login User",
        },
    )
    response = await client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "password123",
            "name": "Test User",
        },
    )
    response = await client.post(
        "/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_user_can_access_me(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "email": "authenticated@example.com",
            "password": "password123",
            "name": "Authenticated User",
        },
    )
    login_response = await client.post(
        "/auth/login",
        json={
            "email": "authenticated@example.com",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    response = await client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "authenticated@example.com"
    assert data["name"] == "Authenticated User"
    assert data["role"] == "MEMBER"
    assert data["is_active"] is True
