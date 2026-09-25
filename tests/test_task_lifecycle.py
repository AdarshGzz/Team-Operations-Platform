import pytest


@pytest.mark.asyncio
async def test_task_can_be_marked_in_progress(
    client,
    manager_token,
    task,
):
    response = await client.patch(
        f"/tasks/{task.id}/status",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
        json={
            "status": "IN_PROGRESS",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "IN_PROGRESS"
    assert data["completed_at"] is None


@pytest.mark.asyncio
async def test_status_change_creates_audit_event(
    client,
    manager_token,
    task,
):
    response = await client.patch(
        f"/tasks/{task.id}/status",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
        json={
            "status": "IN_PROGRESS",
        },
    )

    assert response.status_code == 200

    events_response = await client.get(
        f"/tasks/{task.id}/events",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    status_events = [
        event for event in events if event["event_type"] == "STATUS_CHANGED"
    ]

    assert len(status_events) == 1

    assert status_events[0]["payload"]["old_status"] == "TODO"
    assert status_events[0]["payload"]["new_status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_completing_task_sets_completed_at(
    client,
    manager_token,
    task,
):
    response = await client.patch(
        f"/tasks/{task.id}/status",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_completing_task_creates_completed_event(
    client,
    manager_token,
    task,
):
    response = await client.patch(
        f"/tasks/{task.id}/status",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 200

    events_response = await client.get(
        f"/tasks/{task.id}/events",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    completed_events = [event for event in events if event["event_type"] == "COMPLETED"]

    assert len(completed_events) == 1


@pytest.mark.asyncio
async def test_task_update_creates_update_event(
    client,
    manager_token,
    task,
):
    response = await client.patch(
        f"/tasks/{task.id}",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
        json={
            "title": "Updated task title",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 200

    events_response = await client.get(
        f"/tasks/{task.id}/events",
        headers={
            "Authorization": f"Bearer {manager_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    update_events = [event for event in events if event["event_type"] == "UPDATED"]

    assert len(update_events) == 1

    event_payload = update_events[0]["payload"]

    assert event_payload["title"] == "Updated task title"
    assert event_payload["priority"] == "HIGH"
