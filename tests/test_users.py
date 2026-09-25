from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.user import UserRole


def test_admin_can_list_users(
    client: TestClient,
    admin_token: str,
    member_token: str,
) -> None:
    response = client.get(
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


def test_manager_cannot_list_users(
    client: TestClient,
    manager_token: str,
) -> None:
    response = client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
    )

    assert response.status_code == 403


def test_member_cannot_list_users(
    client: TestClient,
    member_token: str,
) -> None:
    response = client.get(
        "/users",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_list_users(
    client: TestClient,
) -> None:
    response = client.get("/users")

    assert response.status_code == 401


def test_admin_can_get_user(
    client: TestClient,
    admin_token: str,
    member_id,
) -> None:
    response = client.get(
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


def test_get_unknown_user_returns_404(
    client: TestClient,
    admin_token: str,
) -> None:
    unknown_user_id = uuid4()

    response = client.get(
        f"/users/{unknown_user_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_admin_can_update_user_role(
    client: TestClient,
    admin_token: str,
    member_id,
) -> None:
    response = client.patch(
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


def test_admin_can_deactivate_user(
    client: TestClient,
    admin_token: str,
    member_id,
) -> None:
    response = client.patch(
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


def test_admin_cannot_deactivate_self(
    client: TestClient,
    admin_token: str,
    admin_id,
) -> None:
    response = client.patch(
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
