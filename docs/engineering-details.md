# Engineering Details

Supplementary detail for the Team Operations Platform. This material was moved out of the
main `README.md` to keep that document concise; it is the same information, at a lower level.

---

## Alembic revision history

The migration chain is linear and the current head is `09a1d1e26b7d`.

| Revision | Down revision | Change |
| --- | --- | --- |
| `d326d83c5f42` | — | Creates `users`. |
| `fb3505825719` | `d326d83c5f42` | Creates `teams`, `tasks`, and `team_members`, plus the task indexes. |
| `0b329e7fd91b` | `fb3505825719` | Creates `task_events`. |
| `ce8b5c3412ab` | `0b329e7fd91b` | No-op revision; the schema was already in sync. |
| `e36b114e6120` | `ce8b5c3412ab` | Adds `OVERDUE` to `task_status` and `UPDATED` to `task_event_type`. |
| `09a1d1e26b7d` | `e36b114e6120` | Adds the same two enum values again, idempotently. |

### Why the enum migrations are hand-written

PostgreSQL enums are real schema objects rather than a check constraint, so adding a member
requires `ALTER TYPE ... ADD VALUE`. Alembic autogenerate does not detect enum member changes,
so these two revisions were written by hand:

```sql
ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'OVERDUE';
ALTER TYPE task_event_type ADD VALUE IF NOT EXISTS 'UPDATED';
```

The `IF NOT EXISTS` clause makes them safe to re-run, which is why the duplicated second
revision is harmless. `downgrade()` is intentionally empty, because PostgreSQL cannot remove
an enum value without recreating the type.

### Autogenerate hooks

`alembic.ini` runs Ruff against every newly generated revision so migration files are never
committed unformatted. The `module` runner is used rather than `exec` so that the interpreter
running Alembic is the one that resolves `ruff`:

```ini
hooks = ruff_format, ruff_check
ruff_format.type = module
ruff_format.module = ruff
ruff_format.options = format REVISION_SCRIPT_FILENAME
ruff_check.type = module
ruff_check.module = ruff
ruff_check.options = check --fix REVISION_SCRIPT_FILENAME
```

---

## Test suite breakdown

The suite contains **58 tests** across seven files.

| File | Tests | Covers |
| --- | --- | --- |
| `test_health.py` | 2 | `/health` and `/health/db` both return `{"status": "ok"}`. |
| `test_auth.py` | 11 | Registration (success, duplicate email `409`, invalid email, short password, and missing name `422`), login (success, wrong password `401`, unknown email `401`), and protected-endpoint behaviour: `401` without a token and `401` with a malformed token, plus `GET /users/me` succeeding with a valid token and never returning password fields. |
| `test_users.py` | 9 | An admin can list, read, and update users; managers and members receive `403` on the admin-only listing; unauthenticated requests receive `401`; unknown ids return `404`; role updates and deactivation work; an admin cannot deactivate themselves (`400`). |
| `test_teams.py` | 16 | Team creation restricted to admins, duplicate names `409`, listing scoped per role, member versus non-member access (`200` versus `403`), manager and member update rules, deletion restricted to admins, deletion of a team that still has tasks rejected with `409`, membership management including duplicate membership `409` and removal. |
| `test_tasks.py` | 8 | Audit events across the task lifecycle: `CREATED`, `ASSIGNED` on creation, `UPDATED`, reassignment producing `UPDATED` then `ASSIGNED`, `STATUS_CHANGED`, `COMPLETED`, event ordering, and a non-member receiving `403` when reading a task's events. |
| `test_task_lifecycle.py` | 5 | Status transitions through the API: moving to `IN_PROGRESS`, the resulting `STATUS_CHANGED` event payload, `completed_at` being set on completion, and the `COMPLETED` event. |
| `test_overdue.py` | 7 | `process_overdue_tasks` driving a real session: `TODO` and `IN_PROGRESS` past-due tasks become `OVERDUE`, the `OVERDUE` event is written with a due date, and future-dated, completed, cancelled, and already-overdue tasks are left untouched. |

### Shared fixtures

`tests/conftest.py` provides:

| Fixture | Purpose |
| --- | --- |
| `database_connection` | Session-scoped connection that owns the outer transaction. |
| `db_session` | Per-test `AsyncSession` joined to that connection with `create_savepoint`. |
| `client` | `httpx.AsyncClient` over `ASGITransport`, with `get_db_session` overridden to the test session. |
| `register_user`, `login_user`, `auth_headers` | Helpers for the auth endpoints. |
| `create_user` | Inserts a user directly through the session. |
| `team_context` | Builds a team containing an admin, a manager, a member, and an outsider. |
| `task` | Creates a task as the team manager and returns the ORM model so tests can mutate it. |
| `admin_token`, `manager_token`, `member_token`, `outsider_token`, `admin_id`, `manager_id`, `member_id`, `team_id` | Convenience accessors onto `team_context`. |

`team_context` is what lets the authorization tests read as short, direct assertions: the
admin, manager, member, and outsider are all built once, so each test can express only the
permission boundary it cares about.

### Why the overdue tests call the service directly

`test_overdue.py` calls `process_overdue_tasks(db_session)` rather than waiting for the
five-minute background loop. The function takes an injectable session precisely so that the
sweep can be exercised inside the test transaction, which keeps those tests fast and
deterministic while still running real SQL against real PostgreSQL.
