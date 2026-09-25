from uuid import UUID

import pytest
from httpx import AsyncClient

from app.models.user import UserRole


@pytest.mark.asyncio
async def test_admin_can_create_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-team-create@example.com",
        role=UserRole.ADMIN,
        name="Admin",
    )

    token = await login_user(
        email=admin.email,
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Engineering",
            "description": "Engineering team",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Engineering"
    assert data["description"] == "Engineering team"
    assert "id" in data

    UUID(data["id"])


@pytest.mark.asyncio
async def test_member_cannot_create_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    member = await create_user(
        email="member-create-team@example.com",
        role=UserRole.MEMBER,
    )

    token = await login_user(
        email=member.email,
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Unauthorized Team",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_create_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    manager = await create_user(
        email="manager-create-team@example.com",
        role=UserRole.MANAGER,
    )

    token = await login_user(
        email=manager.email,
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Unauthorized Team",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_team_name_returns_conflict(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-duplicate-team@example.com",
        role=UserRole.ADMIN,
    )

    token = await login_user(
        email=admin.email,
    )

    payload = {
        "name": "Duplicate Engineering",
        "description": "First team",
    }

    first_response = await client.post(
        "/teams",
        json=payload,
        headers=auth_headers(token),
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        "/teams",
        json={
            **payload,
            "description": "Second team",
        },
        headers=auth_headers(token),
    )

    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_authenticated_user_can_list_teams(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-list-teams@example.com",
        role=UserRole.ADMIN,
    )

    token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "List Engineering",
            "description": "Engineering",
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201

    response = await client.get(
        "/teams",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert any(team["name"] == "List Engineering" for team in data)


@pytest.mark.asyncio
async def test_user_without_token_cannot_list_teams(
    client: AsyncClient,
):
    response = await client.get("/teams")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_team_member_can_access_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-team-access@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="member-team-access@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Member Access Team",
            "description": "Team access test",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    member_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert member_response.status_code == 201

    member_token = await login_user(
        email=member.email,
    )

    response = await client.get(
        f"/teams/{team_id}",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == team_id
    assert data["name"] == "Member Access Team"


@pytest.mark.asyncio
async def test_non_member_cannot_access_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-team-isolation@example.com",
        role=UserRole.ADMIN,
    )

    outsider = await create_user(
        email="outsider-team-isolation@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Private Team",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    outsider_token = await login_user(
        email=outsider.email,
    )

    response = await client.get(
        f"/teams/{team_id}",
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_update_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    manager = await create_user(
        email="manager-update-team@example.com",
        role=UserRole.MANAGER,
    )

    token = await login_user(
        email=manager.email,
    )

    # Manager needs membership before manager-level team access.
    admin = await create_user(
        email="admin-manager-team@example.com",
        role=UserRole.ADMIN,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Manager Update Team",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{manager.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    response = await client.patch(
        f"/teams/{team_id}",
        json={
            "name": "Updated Manager Team",
            "description": "Updated description",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated Manager Team"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_member_cannot_update_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-member-update@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="member-team-update@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Member Cannot Update",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    member_token = await login_user(
        email=member.email,
    )

    response = await client.patch(
        f"/teams/{team_id}",
        json={
            "name": "Unauthorized Update",
        },
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_delete_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-delete-team@example.com",
        role=UserRole.ADMIN,
    )

    token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Delete Team",
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    response = await client.delete(
        f"/teams/{team_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204

    get_response = await client.get(
        f"/teams/{team_id}",
        headers=auth_headers(token),
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_manager_cannot_delete_team(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-manager-delete@example.com",
        role=UserRole.ADMIN,
    )

    manager = await create_user(
        email="manager-delete-team@example.com",
        role=UserRole.MANAGER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Manager Cannot Delete",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{manager.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    manager_token = await login_user(
        email=manager.email,
    )

    response = await client.delete(
        f"/teams/{team_id}",
        headers=auth_headers(manager_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_add_member(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-add-member@example.com",
        role=UserRole.ADMIN,
    )

    manager = await create_user(
        email="manager-add-member@example.com",
        role=UserRole.MANAGER,
    )

    member = await create_user(
        email="member-add-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Membership Team",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    manager_membership = await client.post(
        f"/teams/{team_id}/members/{manager.id}",
        headers=auth_headers(admin_token),
    )

    assert manager_membership.status_code == 201

    manager_token = await login_user(
        email=manager.email,
    )

    member_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(manager_token),
    )

    assert member_response.status_code == 201

    data = member_response.json()

    assert data["team_id"] == team_id
    assert data["user_id"] == str(member.id)


@pytest.mark.asyncio
async def test_duplicate_team_membership_returns_conflict(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-duplicate-member@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="member-duplicate-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Duplicate Membership Team",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    first_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_manager_can_remove_member(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-remove-member@example.com",
        role=UserRole.ADMIN,
    )

    manager = await create_user(
        email="manager-remove-member@example.com",
        role=UserRole.MANAGER,
    )

    member = await create_user(
        email="member-remove-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Remove Member Team",
        },
        headers=auth_headers(admin_token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    manager_membership = await client.post(
        f"/teams/{team_id}/members/{manager.id}",
        headers=auth_headers(admin_token),
    )

    assert manager_membership.status_code == 201

    manager_token = await login_user(
        email=manager.email,
    )

    member_membership = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(manager_token),
    )

    assert member_membership.status_code == 201

    response = await client.delete(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(manager_token),
    )

    assert response.status_code == 204

    members_response = await client.get(
        f"/teams/{team_id}/members",
        headers=auth_headers(manager_token),
    )

    assert members_response.status_code == 200

    members = members_response.json()

    assert all(member_data["user_id"] != str(member.id) for member_data in members)


@pytest.mark.asyncio
async def test_cannot_delete_team_with_tasks(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="admin-delete-team-tasks@example.com",
        role=UserRole.ADMIN,
    )

    token = await login_user(
        email=admin.email,
    )

    create_response = await client.post(
        "/teams",
        json={
            "name": "Team With Tasks",
        },
        headers=auth_headers(token),
    )

    assert create_response.status_code == 201

    team_id = create_response.json()["id"]

    task_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Blocking task",
        },
        headers=auth_headers(token),
    )

    assert task_response.status_code == 201

    response = await client.delete(
        f"/teams/{team_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A team cannot be deleted while it contains tasks"
    )

    # The team must survive the rejected delete.
    get_response = await client.get(
        f"/teams/{team_id}",
        headers=auth_headers(token),
    )

    assert get_response.status_code == 200
