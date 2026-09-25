from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.user import UserRole


@pytest.mark.asyncio
async def test_admin_can_list_users(
    client: AsyncClient,
    admin_token: str,
    member_token: str,
) -> None:
    response = await client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 2

    for user in data:
        assert "id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert "is_active" in user


@pytest.mark.asyncio
async def test_manager_cannot_list_users(
    client: AsyncClient,
    manager_token: str,
) -> None:
    response = await client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_member_cannot_list_users(
    client: AsyncClient,
    member_token: str,
) -> None:
    response = await client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_list_users(
    client: AsyncClient,
) -> None:
    response = await client.get("/users")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_get_user(
    client: AsyncClient,
    admin_token: str,
    member_id,
) -> None:
    response = await client.get(
        f"/users/{member_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(member_id)
    assert "email" in data
    assert "name" in data
    assert "role" in data
    assert "is_active" in data


@pytest.mark.asyncio
async def test_get_unknown_user_returns_404(
    client: AsyncClient,
    admin_token: str,
) -> None:
    unknown_user_id = uuid4()

    response = await client.get(
        f"/users/{unknown_user_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_admin_can_update_user_role(
    client: AsyncClient,
    admin_token: str,
    member_id,
) -> None:
    response = await client.patch(
        f"/users/{member_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "role": UserRole.MANAGER.value,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(member_id)
    assert data["role"] == UserRole.MANAGER.value
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_admin_can_deactivate_user(
    client: AsyncClient,
    admin_token: str,
    member_id,
) -> None:
    response = await client.patch(
        f"/users/{member_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(member_id)
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(
    client: AsyncClient,
    admin_token: str,
    admin_id,
) -> None:
    response = await client.patch(
        f"/users/{admin_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == ("You cannot deactivate your own account")
