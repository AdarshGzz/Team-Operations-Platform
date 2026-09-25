import pytest
from httpx import AsyncClient

from app.models.task import Task
from app.models.task_event import TaskEventType


async def _events(
    client: AsyncClient,
    headers: dict[str, str],
    task_id,
) -> list[dict]:
    response = await client.get(
        f"/tasks/{task_id}/events",
        headers=headers,
    )

    assert response.status_code == 200

    return response.json()


async def _change_status(
    client: AsyncClient,
    headers: dict[str, str],
    task_id,
    status: str,
):
    return await client.patch(
        f"/tasks/{task_id}/status",
        headers=headers,
        json={
            "status": status,
        },
    )


@pytest.mark.asyncio
async def test_task_can_be_marked_completed(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    response = await _change_status(
        client,
        auth_headers(manager_token),
        task.id,
        "COMPLETED",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_completed_at_is_cleared_when_task_is_reopened(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    headers = auth_headers(manager_token)

    completed = await _change_status(
        client,
        headers,
        task.id,
        "COMPLETED",
    )

    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    reopened = await _change_status(
        client,
        headers,
        task.id,
        "IN_PROGRESS",
    )

    assert reopened.status_code == 200

    data = reopened.json()

    assert data["status"] == "IN_PROGRESS"
    assert data["completed_at"] is None


@pytest.mark.asyncio
async def test_completed_task_creates_audit_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    headers = auth_headers(manager_token)

    response = await _change_status(
        client,
        headers,
        task.id,
        "COMPLETED",
    )

    assert response.status_code == 200

    events = await _events(client, headers, task.id)

    completed_events = [
        event for event in events if event["event_type"] == TaskEventType.COMPLETED
    ]

    assert len(completed_events) == 1
    assert completed_events[0]["payload"]["old_status"] == "TODO"
    assert completed_events[0]["payload"]["new_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_status_change_creates_status_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    headers = auth_headers(manager_token)

    response = await _change_status(
        client,
        headers,
        task.id,
        "IN_PROGRESS",
    )

    assert response.status_code == 200

    events = await _events(client, headers, task.id)

    status_events = [
        event for event in events if event["event_type"] == TaskEventType.STATUS_CHANGED
    ]

    assert len(status_events) == 1
    assert status_events[0]["payload"]["old_status"] == "TODO"
    assert status_events[0]["payload"]["new_status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_unchanged_status_creates_no_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    headers = auth_headers(manager_token)

    response = await _change_status(
        client,
        headers,
        task.id,
        "TODO",
    )

    assert response.status_code == 200

    events = await _events(client, headers, task.id)

    assert [
        event for event in events if event["event_type"] == TaskEventType.STATUS_CHANGED
    ] == []


@pytest.mark.asyncio
async def test_title_change_creates_updated_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    headers = auth_headers(manager_token)

    response = await client.patch(
        f"/tasks/{task.id}",
        headers=headers,
        json={
            "title": "Renamed Task",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Task"

    events = await _events(client, headers, task.id)

    updated_events = [
        event for event in events if event["event_type"] == TaskEventType.UPDATED
    ]

    assert len(updated_events) == 1
    assert updated_events[0]["payload"]["title"] == "Renamed Task"


@pytest.mark.asyncio
async def test_assignment_creates_assigned_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    team_context,
    task: Task,
):
    headers = auth_headers(manager_token)

    response = await client.patch(
        f"/tasks/{task.id}",
        headers=headers,
        json={
            "assignee_id": str(team_context.member.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == str(team_context.member.id)

    events = await _events(client, headers, task.id)

    assigned_events = [
        event for event in events if event["event_type"] == TaskEventType.ASSIGNED
    ]

    assert len(assigned_events) == 1
    assert assigned_events[0]["payload"]["old_assignee_id"] is None
    assert assigned_events[0]["payload"]["new_assignee_id"] == str(
        team_context.member.id
    )


@pytest.mark.asyncio
async def test_task_creation_records_created_event(
    client: AsyncClient,
    manager_token: str,
    auth_headers,
    task: Task,
):
    events = await _events(client, auth_headers(manager_token), task.id)

    created_events = [
        event for event in events if event["event_type"] == TaskEventType.CREATED
    ]

    assert len(created_events) == 1
    assert created_events[0]["payload"]["title"] == task.title
