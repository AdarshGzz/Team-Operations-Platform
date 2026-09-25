import pytest
from httpx import AsyncClient

from app.models.user import UserRole


@pytest.mark.asyncio
async def test_team_member_can_create_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    user = await create_user(
        email="task-creator@example.com",
        role=UserRole.MEMBER,
    )

    admin = await create_user(
        email="task-team-admin@example.com",
        role=UserRole.ADMIN,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Creation Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{user.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    user_token = await login_user(email=user.email)

    response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Implement authentication",
            "description": "Implement JWT authentication",
            "priority": "HIGH",
        },
        headers=auth_headers(user_token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Implement authentication"
    assert data["description"] == "Implement JWT authentication"
    assert data["priority"] == "HIGH"
    assert data["status"] == "TODO"
    assert data["team_id"] == team_id
    assert data["created_by"] == str(user.id)
    assert data["assignee_id"] is None
    assert data["completed_at"] is None


@pytest.mark.asyncio
async def test_outsider_cannot_create_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-outsider-admin@example.com",
        role=UserRole.ADMIN,
    )

    outsider = await create_user(
        email="task-outsider@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Private Task Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    outsider_token = await login_user(email=outsider.email)

    response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Unauthorized task",
        },
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_task_can_be_created_with_assignee(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-assignment-admin@example.com",
        role=UserRole.ADMIN,
    )

    creator = await create_user(
        email="task-assignment-creator@example.com",
        role=UserRole.MEMBER,
    )

    assignee = await create_user(
        email="task-assignment-assignee@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Assignment Validation Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    for user in (creator, assignee):
        response = await client.post(
            f"/teams/{team_id}/members/{user.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 201

    creator_token = await login_user(email=creator.email)

    response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Assigned task",
            "assignee_id": str(assignee.id),
        },
        headers=auth_headers(creator_token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["assignee_id"] == str(assignee.id)


@pytest.mark.asyncio
async def test_task_cannot_be_assigned_to_outsider(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-invalid-assignee-admin@example.com",
        role=UserRole.ADMIN,
    )

    creator = await create_user(
        email="task-invalid-assignee-creator@example.com",
        role=UserRole.MEMBER,
    )

    outsider = await create_user(
        email="task-invalid-assignee-outsider@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Assignee Validation Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{creator.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    creator_token = await login_user(email=creator.email)

    response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Invalid assignment",
            "assignee_id": str(outsider.id),
        },
        headers=auth_headers(creator_token),
    )

    assert response.status_code == 400
    assert "active member of the team" in response.json()["detail"]


@pytest.mark.asyncio
async def test_team_tasks_can_be_listed(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-list-admin@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="task-list-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Listing Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    member_token = await login_user(email=member.email)

    for title in ("Task One", "Task Two"):
        response = await client.post(
            f"/teams/{team_id}/tasks",
            json={
                "title": title,
            },
            headers=auth_headers(member_token),
        )

        assert response.status_code == 201

    response = await client.get(
        f"/teams/{team_id}/tasks",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200

    data = response.json()

    titles = {task["title"] for task in data}

    assert {"Task One", "Task Two"} <= titles


@pytest.mark.asyncio
async def test_team_outsider_cannot_list_tasks(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-list-isolation-admin@example.com",
        role=UserRole.ADMIN,
    )

    outsider = await create_user(
        email="task-list-isolation-outsider@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Isolation Team",
        },
        headers=auth_headers(admin_token),
    )

    assert team_response.status_code == 201

    team_id = team_response.json()["id"]

    outsider_token = await login_user(email=outsider.email)

    response = await client.get(
        f"/teams/{team_id}/tasks",
        headers=auth_headers(outsider_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_task_can_be_retrieved(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-get-admin@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="task-get-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Retrieval Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    member_token = await login_user(email=member.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Retrievable Task",
        },
        headers=auth_headers(member_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    response = await client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == task_id
    assert data["title"] == "Retrievable Task"


@pytest.mark.asyncio
async def test_task_update_by_assignee(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-update-admin@example.com",
        role=UserRole.ADMIN,
    )

    assignee = await create_user(
        email="task-update-assignee@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Update Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    membership_response = await client.post(
        f"/teams/{team_id}/members/{assignee.id}",
        headers=auth_headers(admin_token),
    )

    assert membership_response.status_code == 201

    assignee_token = await login_user(email=assignee.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Original title",
            "assignee_id": str(assignee.id),
        },
        headers=auth_headers(assignee_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={
            "title": "Updated title",
            "priority": "HIGH",
        },
        headers=auth_headers(assignee_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "Updated title"
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_unassigned_member_cannot_update_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-update-denied-admin@example.com",
        role=UserRole.ADMIN,
    )

    creator = await create_user(
        email="task-update-denied-creator@example.com",
        role=UserRole.MEMBER,
    )

    other_member = await create_user(
        email="task-update-denied-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Task Update Authorization Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    for user in (creator, other_member):
        response = await client.post(
            f"/teams/{team_id}/members/{user.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 201

    creator_token = await login_user(email=creator.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Protected task",
        },
        headers=auth_headers(creator_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    other_token = await login_user(email=other_member.email)

    response = await client.patch(
        f"/tasks/{task_id}",
        json={
            "title": "Unauthorized update",
        },
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_update_team_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-manager-update-admin@example.com",
        role=UserRole.ADMIN,
    )

    manager = await create_user(
        email="task-manager-update@example.com",
        role=UserRole.MANAGER,
    )

    member = await create_user(
        email="task-manager-update-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Manager Task Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    for user in (manager, member):
        response = await client.post(
            f"/teams/{team_id}/members/{user.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 201

    member_token = await login_user(email=member.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Manager editable task",
        },
        headers=auth_headers(member_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    manager_token = await login_user(email=manager.email)

    response = await client.patch(
        f"/tasks/{task_id}",
        json={
            "title": "Updated by manager",
        },
        headers=auth_headers(manager_token),
    )

    assert response.status_code == 200

    assert response.json()["title"] == "Updated by manager"


@pytest.mark.asyncio
async def test_member_cannot_delete_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-delete-member-admin@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="task-delete-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Member Delete Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201

    member_token = await login_user(email=member.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Cannot delete",
        },
        headers=auth_headers(member_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    response = await client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_delete_task(
    client: AsyncClient,
    create_user,
    login_user,
    auth_headers,
):
    admin = await create_user(
        email="task-delete-admin@example.com",
        role=UserRole.ADMIN,
    )

    member = await create_user(
        email="task-delete-admin-member@example.com",
        role=UserRole.MEMBER,
    )

    admin_token = await login_user(email=admin.email)

    team_response = await client.post(
        "/teams",
        json={
            "name": "Admin Delete Task Team",
        },
        headers=auth_headers(admin_token),
    )

    team_id = team_response.json()["id"]

    response = await client.post(
        f"/teams/{team_id}/members/{member.id}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201

    member_token = await login_user(email=member.email)

    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        json={
            "title": "Delete me",
        },
        headers=auth_headers(member_token),
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers(admin_token),
    )

    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/tasks/{task_id}",
        headers=auth_headers(admin_token),
    )

    assert get_response.status_code == 404
