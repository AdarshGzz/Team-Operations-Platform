import pytest


@pytest.mark.asyncio
async def test_task_creation_creates_created_event(
    client,
    member_token,
    team_id,
):
    response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Event Test Task",
            "description": "Testing task events",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 201

    task = response.json()

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 1

    assert events[0]["task_id"] == task["id"]
    assert events[0]["event_type"] == "CREATED"

    assert events[0]["payload"]["title"] == "Event Test Task"
    assert events[0]["payload"]["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_task_creation_with_assignee_creates_assigned_event(
    client,
    member_token,
    team_id,
    member_id,
):
    response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Assigned Event Task",
            "assignee_id": str(member_id),
        },
    )

    assert response.status_code == 201

    task = response.json()

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 2

    assert events[0]["event_type"] == "CREATED"
    assert events[1]["event_type"] == "ASSIGNED"

    assert events[1]["payload"]["assignee_id"] == str(member_id)


@pytest.mark.asyncio
async def test_task_update_creates_updated_event(
    client,
    member_token,
    team_id,
    member_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Original Title",
            "priority": "LOW",
            "assignee_id": str(member_id),
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    update_response = await client.patch(
        f"/tasks/{task['id']}",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Updated Title",
            "priority": "HIGH",
        },
    )

    assert update_response.status_code == 200

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 3

    assert events[0]["event_type"] == "CREATED"
    assert events[1]["event_type"] == "ASSIGNED"
    assert events[2]["event_type"] == "UPDATED"

    assert events[2]["payload"]["title"] == "Updated Title"
    assert events[2]["payload"]["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_task_assignee_change_creates_assigned_event(
    client,
    member_token,
    team_id,
    member_id,
    manager_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Reassignment Test",
            "assignee_id": str(member_id),
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    update_response = await client.patch(
        f"/tasks/{task['id']}",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "assignee_id": str(manager_id),
        },
    )

    assert update_response.status_code == 200

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 4

    assert [event["event_type"] for event in events] == [
        "CREATED",
        "ASSIGNED",
        "UPDATED",
        "ASSIGNED",
    ]

    assert events[2]["payload"]["title"] == "Reassignment Test"

    assert events[3]["payload"]["old_assignee_id"] == str(member_id)
    assert events[3]["payload"]["new_assignee_id"] == str(manager_id)


@pytest.mark.asyncio
async def test_status_change_creates_status_changed_event(
    client,
    member_token,
    team_id,
    member_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Status Event Test",
            "assignee_id": str(member_id),
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    update_response = await client.patch(
        f"/tasks/{task['id']}/status",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "status": "IN_PROGRESS",
        },
    )

    assert update_response.status_code == 200

    assert update_response.json()["status"] == "IN_PROGRESS"

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 3

    assert events[0]["event_type"] == "CREATED"
    assert events[1]["event_type"] == "ASSIGNED"
    assert events[2]["event_type"] == "STATUS_CHANGED"

    assert events[2]["payload"]["old_status"] == "TODO"
    assert events[2]["payload"]["new_status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_completing_task_creates_completed_event(
    client,
    member_token,
    team_id,
    member_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Completion Event Test",
            "assignee_id": str(member_id),
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    update_response = await client.patch(
        f"/tasks/{task['id']}/status",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "status": "COMPLETED",
        },
    )

    assert update_response.status_code == 200

    updated_task = update_response.json()

    assert updated_task["status"] == "COMPLETED"
    assert updated_task["completed_at"] is not None

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 3

    assert events[0]["event_type"] == "CREATED"
    assert events[1]["event_type"] == "ASSIGNED"
    assert events[2]["event_type"] == "COMPLETED"

    assert events[2]["payload"]["old_status"] == "TODO"
    assert events[2]["payload"]["new_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_task_events_are_returned_in_creation_order(
    client,
    member_token,
    team_id,
    member_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Event Ordering Test",
            "assignee_id": str(member_id),
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    await client.patch(
        f"/tasks/{task['id']}/status",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "status": "IN_PROGRESS",
        },
    )

    await client.patch(
        f"/tasks/{task['id']}/status",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "status": "COMPLETED",
        },
    )

    events_response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert [event["event_type"] for event in events] == [
        "CREATED",
        "ASSIGNED",
        "STATUS_CHANGED",
        "COMPLETED",
    ]

    timestamps = [event["created_at"] for event in events]

    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_task_events_require_task_access(
    client,
    member_token,
    outsider_token,
    team_id,
):
    create_response = await client.post(
        f"/teams/{team_id}/tasks",
        headers={
            "Authorization": f"Bearer {member_token}",
        },
        json={
            "title": "Private Event Test",
        },
    )

    assert create_response.status_code == 201

    task = create_response.json()

    response = await client.get(
        f"/tasks/{task['id']}/events",
        headers={
            "Authorization": f"Bearer {outsider_token}",
        },
    )

    assert response.status_code == 403
