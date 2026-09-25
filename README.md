# Team Operations Platform

A REST API for managing **users**, **teams**, and **tasks**, with role-based access control and an append-only audit trail of every change made to a task.

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic. An in-process scheduler flags overdue tasks automatically.

---

## Assignment Requirements → Implementation

| Requirement | Implementation |
| --- | --- |
| Users | Registration, profile (`GET /users/me`), admin listing/updates, `ADMIN`/`MANAGER`/`MEMBER` roles, activation state |
| Teams | Team CRUD, membership management, per-role visibility |
| Tasks | Task CRUD, validated assignment, status lifecycle, per-team listing |
| Admin / Manager / Member | `require_roles` plus team- and task-scoped authorization dependencies |
| Authentication | JWT bearer tokens (PyJWT), Argon2 password hashing (`pwdlib`) |
| Authorization | Role and resource-scope checks; matrices below |
| API design | REST endpoints, Pydantic schemas, OpenAPI at `/docs` |
| Database modelling | PostgreSQL, five tables, UUID keys, explicit relationships |
| Data integrity | `RESTRICT`/`CASCADE`/`SET NULL` foreign keys, composite primary key, unique constraints, indexes |
| Validation | Pydantic field constraints plus service-layer business rules |
| Performance | Indexes on the queried columns; fully async database access |
| Testing | pytest + pytest-asyncio against the real app and real PostgreSQL |
| Maintainability | Layered: routes → dependencies → services → models |
| Non-trivial capability | Background overdue-task scheduler on the FastAPI lifespan |
| Documentation | This README plus [`docs/engineering-details.md`](docs/engineering-details.md) |

---

## Quick Start

```bash
git clone <repository-url>
cd Assignment

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Set DATABASE_URL (postgresql+asyncpg://...) and JWT_SECRET_KEY in .env

alembic upgrade head
uvicorn app.main:app --reload
```

Docs: **http://127.0.0.1:8000/docs** (Swagger UI) · **/redoc** · **/openapi.json**

```bash
python -m scripts.create_admin   # first admin (registration only creates MEMBER)
pytest                            # tests; requires TEST_DATABASE_URL
```

---

## Tech Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12 – 3.14 (`requires-python = ">=3.12,<3.15"`) |
| Web framework | FastAPI, served by Uvicorn |
| Database | PostgreSQL, accessed via SQLAlchemy 2.0 async + `asyncpg` (+ `greenlet`) |
| Migrations | Alembic, async `env.py` |
| Validation / settings | Pydantic v2, `pydantic-settings` |
| Auth | `pwdlib` (Argon2) for hashing, PyJWT (HS256) for tokens |
| Tooling | Ruff for lint + format; pytest, pytest-asyncio, httpx for tests |

---

## Setup and Run Instructions

### Prerequisites

- **Python 3.12, 3.13, or 3.14** (`>=3.12,<3.15`; verified on 3.14).
- **PostgreSQL reachable over TLS.** The engine is created with `connect_args={"ssl": True}`, so a local PostgreSQL without TLS will not connect without changing that code.
- `pip` (the project builds through setuptools via `pyproject.toml`).
- Docker + Compose are optional.

### Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Runtime dependencies are in `[project.dependencies]`; `alembic`, `httpx`, `pytest`, `pytest-asyncio`, `python-dotenv`, and `ruff` are in the `dev` extra. `requirements.txt` is a pinned mirror of the same set for requirements-file installs — `pyproject.toml` is the source of truth.

### Configure

```bash
cp .env.example .env
```

Set at minimum `DATABASE_URL` and `JWT_SECRET_KEY`, then note:

- Use the **`postgresql+asyncpg://`** scheme. Plain `postgresql://` selects the synchronous psycopg2 driver and fails.
- Do **not** append `?sslmode=...` or `&channel_binding=...` — those are libpq/psycopg2 parameters that `asyncpg` rejects. SSL is applied via `connect_args` instead.
- Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
TEST_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Migrate, run, and explore

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Serves on `http://127.0.0.1:8000`. Every route except the health checks and the two auth endpoints needs a bearer token, so the intended flow is `POST /auth/register` → `POST /auth/login` → click **Authorize** in Swagger UI and paste the `access_token`.

### Tests

```bash
pytest          # TEST_DATABASE_URL must be set; see Testing
```

### Docker (optional)

```bash
docker compose up --build
```

The `api` service builds from `Dockerfile`, publishes port `8000`, and reads `.env` via `env_file`. The database stays external — the compose file defines no database service.

---

## Environment Variables

Defined in `app/core/config.py` with `pydantic-settings`, read from the environment and `.env`, matched case-insensitively (`DATABASE_URL` ≡ `database_url`).

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | **Yes** | — | Application engine and Alembic |
| `JWT_SECRET_KEY` | **Yes** | — | Signing and verifying tokens |
| `JWT_ALGORITHM` | No | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Token lifetime |
| `TEST_DATABASE_URL` | **Yes, for tests** | — | Read by `tests/conftest.py`; not part of `Settings` |

`Settings` also declares `app_name`, `app_version`, and `app_env`, which are validated but read nowhere — they currently have no runtime effect.

---

## Architecture Overview

Layered, with dependencies pointing inward: routes depend on services, services on models, and only `app/core/database.py` knows how a session is created.

```mermaid
flowchart LR
    Client["Client"] --> Routes["API layer<br/>app/api/routes"]
    Routes --> Deps["Authentication<br/>HTTPBearer + get_current_user"]
    Deps --> Authz{"Authorization<br/>require_roles / require_*_access"}
    Authz -->|"401 / 403 / 404"| Client
    Authz -->|"authorized"| Services["Service layer<br/>app/services"]
    Services --> Models["ORM models<br/>app/models"]
    Models --> DB[("PostgreSQL")]
    Services --> Events["TaskEvent audit rows"]
    Scheduler["Overdue scheduler<br/>lifespan task"] --> Services
```

| Layer | Responsibility |
| --- | --- |
| `app/main.py` | App creation, router registration, health endpoints, `lifespan` (starts/stops the scheduler) |
| `app/api/deps.py` | `HTTPBearer` scheme + `get_current_user`: decode JWT, load user, reject invalid tokens and inactive users |
| `app/api/routes/` | HTTP layer (`auth`, `users`, `teams`, `tasks`): validate input, attach authorization, map exceptions to status codes |
| `app/core/` | Settings, engine/session dependency, password + JWT helpers, and the three authorization modules |
| `app/models/` | Declarative models, UUID/timestamp mixins, enum types |
| `app/schemas/` | Pydantic request/response models, separate from the ORM |
| `app/services/` | Business logic and persistence; owns transactions and audit-event writes |

**Request flow** — `PATCH /tasks/{task_id}/status`:

1. **Route** matched in `app/api/routes/tasks.py`.
2. **Validation** — `TaskStatusUpdateRequest` rejects an unknown status with `422` before handler code runs.
3. **Authentication** — `require_task_manage_access` depends on `get_current_user`: `HTTPBearer` extracts the token (`401` if missing/malformed), the signature and expiry are verified, and the user is loaded with `is_active = true`.
4. **Authorization** — the task is loaded (`404` if absent) and the role rules below are enforced, raising `403` when not permitted.
5. **Service** — `task_service.update_status(...)` applies the change, appends a `TaskEvent`, commits, and refreshes.
6. **Response** — `TaskResponse.model_validate(...)` serialises the ORM object.

Sessions are never threaded through layers by hand: `get_db_session` yields one `AsyncSession` per request and closes it afterwards, and the tests override exactly that dependency.

---

## Domain Model

Five tables — `users`, `teams`, `team_members`, `tasks`, `task_events` — plus Alembic's `alembic_version`.

```mermaid
erDiagram
    USERS ||--o{ TEAM_MEMBERS : "is a member of"
    TEAMS ||--o{ TEAM_MEMBERS : "has members"
    TEAMS ||--o{ TASKS : "contains"
    USERS ||--o{ TASKS : "created_by"
    USERS |o--o{ TASKS : "assignee_id"
    TASKS ||--o{ TASK_EVENTS : "audit trail"

    USERS {
        uuid id PK
        varchar email UK
        varchar password_hash
        enum role
        boolean is_active
    }
    TEAMS {
        uuid id PK
        varchar name UK
        text description
    }
    TEAM_MEMBERS {
        uuid team_id PK
        uuid user_id PK
        timestamptz joined_at
    }
    TASKS {
        uuid id PK
        varchar title
        uuid team_id
        uuid created_by
        uuid assignee_id
        enum status
        enum priority
        timestamptz due_at
        timestamptz completed_at
    }
    TASK_EVENTS {
        uuid id PK
        uuid task_id
        enum event_type
        json payload
        timestamptz created_at
    }
```

- **User ↔ Team** is many-to-many through `team_members`, whose composite primary key `(team_id, user_id)` makes duplicate memberships impossible.
- **Team → Task** is strict: `tasks.team_id` is `ON DELETE RESTRICT`.
- **Task → User** twice: `created_by` (`RESTRICT`, the author) and `assignee_id` (`SET NULL`, nullable, the current owner).
- **Task → TaskEvent** cascades (`delete-orphan` + `ON DELETE CASCADE`), so deleting a task removes its history.

`users`, `teams`, and `tasks` use `UUIDPrimaryKeyMixin` (Python-side `uuid4`) and `TimestampMixin` (`created_at`/`updated_at` with `server_default=now()`, plus `onupdate`). Enums are `enum.StrEnum` classes backed by native PostgreSQL types (`user_role`, `task_status`, `task_priority`, `task_event_type`).

Indexes beyond primary/unique keys: `ix_tasks_team_status` `(team_id, status)`, `ix_tasks_assignee_status` `(assignee_id, status)`, `ix_tasks_due_at` `(due_at)`, `ix_task_events_task_event_type` `(task_id, event_type)`, `ix_users_email` (unique).

---

## Task Events (Audit History)

Every task mutation appends a row to `task_events`. No endpoint edits or deletes an event; they disappear only when their task is deleted.

| Event | Emitted when | Payload |
| --- | --- | --- |
| `CREATED` | Task created | `title`, `priority` |
| `ASSIGNED` | Created with an assignee / assignee changed | `assignee_id`, or `old_assignee_id` + `new_assignee_id` |
| `UPDATED` | Any tracked field changed (`title`, `description`, `priority`, `assignee_id`, `due_at`) | `title`, `priority`, `due_at` |
| `STATUS_CHANGED` | Status changed to anything other than `COMPLETED` | `old_status`, `new_status` |
| `COMPLETED` | Status changed to `COMPLETED` | `old_status`, `new_status` |
| `OVERDUE` | Scheduler flagged a past-due task | `due_at` |

Consequences worth knowing:

- A reassignment writes **two** events — `UPDATED` (since `assignee_id` is tracked) then `ASSIGNED`.
- A no-op status change, or an update where nothing changed, writes nothing.
- `UPDATED`'s payload never echoes the description, even when only the description changed.
- `GET /tasks/{task_id}/events` orders by `created_at` ascending; events written in one transaction share a timestamp, so their relative order within a request is not defined by that sort alone.

The result is an append-only chronological record of task mutations, assignments, and lifecycle changes.

---

## Overdue Task Processing

`app/services/task_scheduler.py` — the project's non-trivial backend capability.

- `process_overdue_tasks(db=None)` selects tasks with a `due_at` in the past whose status is `TODO` or `IN_PROGRESS`; it sets them to `OVERDUE`, writes an `OVERDUE` event carrying the due date, commits once, and returns the count.
- `COMPLETED`, `CANCELLED`, and already-`OVERDUE` tasks are excluded, so finished work is never flipped and overdue tasks are not re-processed.
- The session is injectable: with no argument it opens its own short-lived session (how the scheduler calls it); the tests pass their session so the work stays inside the test transaction.
- `overdue_task_scheduler()` loops forever, sleeping `OVERDUE_CHECK_INTERVAL_SECONDS` (300s). Unexpected exceptions are logged and the loop continues; `CancelledError` is re-raised for clean shutdown.
- It runs from the FastAPI `lifespan` handler and is cancelled on shutdown, so it lives in the web process.

`OVERDUE` is derived, not terminal — a later status change can move the task on, and `completed_at` is only ever set by a transition into `COMPLETED`.

---

## Authentication and Authorization

**Authentication.** `POST /auth/register` hashes the password with `pwdlib`'s `PasswordHash.recommended()` (Argon2) and stores only the hash; every registrant gets `MEMBER`, and `password`/`password_hash` are never returned. `POST /auth/login` returns a JWT signed with `JWT_SECRET_KEY` using `JWT_ALGORITHM`, carrying `sub` (user UUID) and `exp`. Unknown emails, wrong passwords, and inactive accounts all return the same `401 Invalid email or password`, so the endpoint does not reveal which addresses exist. Clients then send `Authorization: Bearer <token>`; `decode_access_token` verifies signature and expiry and `get_current_user` loads the user with `is_active = true`. Tokens are stateless, so there is no revocation, logout, or refresh.

**Roles** are global, one per user.

| Role | Intent |
| --- | --- |
| `ADMIN` | Global administrator |
| `MANAGER` | Manages the teams they belong to |
| `MEMBER` | Works on tasks assigned to them |

`require_roles(...)` returns `403` when the role is not allowed; resource-scoped checks return `404` for a missing row and `403` when the caller is not permitted.

| Operation | ADMIN | MANAGER | MEMBER |
| --- | --- | --- | --- |
| Create / delete team | Yes | No, `403` | No, `403` |
| List teams | All | Only teams they belong to | Only teams they belong to |
| Read team / list members | Any | If a member | If a member |
| Update team, add/remove member | Any | If a member | No, `403` |
| List or create tasks in a team | Any team | Own teams | Own teams |
| Read a task, read its events | Any task | If in the task's team | If in the task's team |
| Update task / change status | Any task | If in the task's team | Only if assigned to them |
| Delete task | Any task | If in the task's team | No, `403` |
| `GET /users`, `GET`/`PATCH /users/{id}` | Yes | No, `403` | No, `403` |
| `GET /users/me` | Yes | Yes | Yes |

`require_team_access` accepts an `ADMIN` and otherwise requires a `team_members` row; `require_team_manager_access` requires the `MANAGER` role *and* membership. `require_task_view_access` and `require_task_manage_access` both resolve the task first — the difference is that a `MEMBER` may only **modify** a task whose `assignee_id` is their own, so a member who created a task but was never assigned it can read it and its history but not change it. Deleting a task combines both mechanisms: the role check, then a team-membership check for managers.

**Service-layer business rules**

- **Assignee validation** — the assignee must be an active member of the task's team (`400`), evaluated at assignment time only.
- **Unique team names** — enforced on create and update (`409`); a team's own name is excluded when updating.
- **Team deletion guard** — a team containing tasks cannot be deleted; the API returns `409 A team cannot be deleted while it contains tasks`.
- **Self-deactivation guard** — an admin cannot deactivate their own account (`400`).

---

## API Documentation

All routes except `/health`, `/health/db`, `/auth/register`, and `/auth/login` require a bearer token.

| Method | Endpoint | Authz | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Liveness; `{"status": "ok"}`, no database access. |
| `GET` | `/health/db` | None | Runs `SELECT 1`; `{"status": "ok"}`. |
| `POST` | `/auth/register` | None | Create an account (`MEMBER`). `201`; `409` duplicate email; `422` invalid. |
| `POST` | `/auth/login` | None | JWT for valid credentials. `200`; `401` bad credentials or inactive. |
| `GET` | `/users/me` | Authenticated | The caller's profile. |
| `GET` | `/users` | `ADMIN` | All users, newest first. |
| `GET` | `/users/{user_id}` | `ADMIN` | One user; `404` if absent. |
| `PATCH` | `/users/{user_id}` | `ADMIN` | Update `role` / `is_active`; `400` when deactivating self. |
| `GET` | `/teams` | Authenticated | `ADMIN`: all teams; others: their teams. By name. |
| `POST` | `/teams` | `ADMIN` | Create a team; `409` duplicate name. |
| `GET` | `/teams/{team_id}` | `ADMIN` or member | `404` absent, `403` not a member. |
| `PATCH` | `/teams/{team_id}` | `ADMIN` or member-manager | Update `name`/`description`; `409` duplicate. |
| `DELETE` | `/teams/{team_id}` | `ADMIN` | `204`; `409` if the team still has tasks; `404` absent. |
| `GET` | `/teams/{team_id}/members` | `ADMIN` or member | Memberships by `joined_at`. |
| `POST` | `/teams/{team_id}/members/{user_id}` | `ADMIN` or member-manager | Add a member; `409` if unknown, inactive, or already a member. |
| `DELETE` | `/teams/{team_id}/members/{user_id}` | `ADMIN` or member-manager | `204`; `404` if not a member. |
| `GET` | `/teams/{team_id}/tasks` | `ADMIN` or member | The team's tasks, newest first. |
| `POST` | `/teams/{team_id}/tasks` | `ADMIN` or member | Create a task; `400` if the assignee is not an active member. |
| `GET` | `/tasks/{task_id}` | `ADMIN` or team member | `404` absent, `403` not permitted. |
| `PATCH` | `/tasks/{task_id}` | `ADMIN`, team manager, or assignee | Update `title`/`description`/`priority`/`assignee_id`/`due_at`; omitted fields unchanged; `400` bad assignee. |
| `PATCH` | `/tasks/{task_id}/status` | `ADMIN`, team manager, or assignee | Change status; `COMPLETED` sets `completed_at`, moving away clears it. |
| `DELETE` | `/tasks/{task_id}` | `ADMIN` or team manager | Delete the task and its events; `204`. |
| `GET` | `/tasks/{task_id}/events` | `ADMIN` or team member | Audit trail in ascending time order. |

Accepted values — `status`: `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `OVERDUE`; `priority`: `LOW`, `MEDIUM`, `HIGH`; `role`: `ADMIN`, `MANAGER`, `MEMBER`.

Common errors: `401` missing/invalid/expired token or inactive user; `403` role or scope failure; `404` missing resource; `409` conflict; `422` body validation.

---

## Database and Migrations

| Table | Purpose | Key constraints |
| --- | --- | --- |
| `users` | Accounts | UUID PK; `email` unique + indexed; `role`/`is_active` defaulted in code |
| `teams` | Teams | UUID PK; `name` unique |
| `team_members` | Membership join | Composite PK `(team_id, user_id)`; both FKs `CASCADE` |
| `tasks` | Tasks | UUID PK; `team_id`/`created_by` `RESTRICT`; `assignee_id` `SET NULL` |
| `task_events` | Append-only audit trail | UUID PK; `task_id` `CASCADE`; JSON column physically named `metadata` |

The payload column is named `metadata` in the database because `metadata` is reserved on SQLAlchemy declarative classes; the attribute is `payload`, mapped explicitly.

**Cascades.** Deleting a team removes its memberships (`CASCADE` + `delete-orphan`) but is *rejected* with `409` while tasks reference it. Deleting a task removes its events. Deleting a user would remove memberships, is blocked by tasks they authored (`RESTRICT`), and unassigns tasks assigned to them (`SET NULL`) — though no user-deletion endpoint exists.

**Alembic.** `migrations/env.py` is the async variant: it overrides the URL from `DATABASE_URL` at runtime (`sqlalchemy.url` in `alembic.ini` is only a placeholder), targets `Base.metadata`, and runs through `async_engine_from_config` with `connection.run_sync(...)`. Post-write hooks run Ruff on every generated revision. The chain is linear with head `09a1d1e26b7d`; because PostgreSQL enums are real types, the two enum additions are hand-written `ALTER TYPE ... ADD VALUE IF NOT EXISTS` statements that autogenerate cannot produce. Full revision history: [`docs/engineering-details.md`](docs/engineering-details.md).

```bash
alembic upgrade head      # apply to latest
alembic current           # applied revision
alembic history           # revision chain
alembic check             # model/schema drift
alembic revision --autogenerate -m "..."
alembic downgrade -1
```

Healthy state: `alembic current` equals the head and `alembic check` reports "No new upgrade operations detected."

---

## Testing

pytest with **pytest-asyncio** in strict mode (`@pytest.mark.asyncio` on tests, `@pytest_asyncio.fixture` on fixtures). Fixture and test loop scopes are both pinned to `session`, since asyncpg connections cannot cross event loops.

No server is started: tests drive the real ASGI app in-process with `httpx.AsyncClient` over `ASGITransport`, so routing, dependencies, validation, and serialisation are genuinely exercised. `conftest.py` loads `.env` and requires `TEST_DATABASE_URL`, failing fast with an explicit error when it is unset.

Isolation works by transaction rollback: a session-scoped fixture opens one connection and an outer transaction, each test gets an `AsyncSession` joined to it with `create_savepoint`, and `get_db_session` is overridden so the application uses that session. The outer transaction is rolled back after every test, so nothing is committed and tests do not leak.

```bash
pytest          # 58 tests across seven modules
pytest -v
```

Coverage: health endpoints; registration/login success and failure paths (`409`, `422`, `401`); admin-only user operations and the self-deactivation guard; team creation/deletion restrictions, role-scoped listing, member vs non-member access, and membership management; the full task event lifecycle and event ordering; `403` for non-members reading task events; and overdue processing (past-due `TODO`/`IN_PROGRESS` tasks become `OVERDUE`, while future-dated, completed, cancelled, and already-overdue ones are untouched). The sweep is invoked directly as `process_overdue_tasks(db_session)` rather than waiting for the background loop, keeping those tests fast and deterministic. Per-file breakdown: [`docs/engineering-details.md`](docs/engineering-details.md).

---

## Important Assumptions

**Users and roles** — one global role per user (no per-team roles); self-registration always yields `MEMBER`, with privileges granted afterwards by an admin or the bootstrap script; emails are compared exactly (only the bootstrap script lowercases input); inactive users cannot authenticate, and tokens for a user later deactivated stop working because `get_current_user` filters on `is_active`.

**Teams and membership** — a team has no owner column, so access derives purely from `team_members` plus the `ADMIN` override; creating a team does not make its creator a member; membership is the only thing granting team-scoped access; a team containing tasks cannot be deleted, which is a deliberate rule rather than an incidental constraint.

**Task ownership and assignment** — `created_by` is recorded but grants no edit rights, so for a `MEMBER` only being the current assignee permits writes; a task belongs to exactly one team and has at most one assignee; the assignee must be an active team member *at assignment time*, and because the FK points at `users` rather than `team_members`, a task can remain assigned to someone who has since left; every `PATCH /tasks/{task_id}` field treats an omitted value as "unchanged", so tasks cannot be unassigned and `description`/`due_at` cannot be cleared.

**Task lifecycle** — no state machine is enforced (any status may follow any other); `completed_at` is set only when entering `COMPLETED` and cleared on leaving; `OVERDUE` is computed by the scheduler and may be superseded by a later change, after which a still-past-due task can be flagged again; a task without `due_at` can never become overdue; `priority` is advisory and never drives ordering or scheduling.

**Event logging** — events are written only by the service layer, in the same transaction as the change they describe; they are immutable through the API; concurrent updates are last-write-wins with no optimistic locking.

**Authentication** — a single JWT secret with no rotation; tokens valid until `exp` with no denylist, so logout is client-side; no password reset or email verification.

**Overdue processing** — the sweep lives in the API process so detection stops with it; multiple workers mean concurrent sweeps, which is effectively idempotent because the selection excludes tasks already `OVERDUE`; the five-minute interval bounds how long a task can remain un-flagged.

---

## Key Engineering Decisions and Trade-offs

| Decision | Why | Trade-off |
| --- | --- | --- |
| **FastAPI** | Dependency injection, validation, and OpenAPI from the same type hints; thin routing and free Swagger UI | Framework indirection in dependency resolution; `Depends()`-in-defaults trips Ruff `B008`, handled with a scoped per-file ignore |
| **SQLAlchemy 2.0 async + asyncpg** | The workload is I/O-bound on the database, so async lets one worker serve far more concurrent requests; asyncpg is the fastest asyncio driver | Harder to debug; `greenlet` needed explicitly; different exception types; asyncpg rejects libpq URL params like `sslmode`, hence `connect_args` for SSL |
| **PostgreSQL** | Native `UUID`, `TIMESTAMPTZ`, `JSON`, and enum types, plus real foreign keys, enforce integrity in the database | Enum values become schema objects, so adding one needs an `ALTER TYPE` migration |
| **Pydantic schemas separate from ORM** | The contract can forbid client-set fields (`completed_at`, `created_by`) and can never leak `password_hash` | Duplication; two near-identical `UserResponse` classes exist |
| **JWT bearer auth** | Stateless, horizontally scalable, easy to test | No revocation without extra infrastructure; a leaked token is valid until it expires |
| **Authorization as dependencies** | Coarse/team/task checks are reusable, so a route cannot silently omit them and rules are testable over HTTP | Task-scoped dependencies re-query the task, loading the row twice per request |
| **Service layer** | Keeps HTTP concerns out of business rules; `TaskService` is the single place deciding audit events; services are directly testable | Extra indirection for thin query wrappers |
| **Alembic** | Versioned, reproducible schema; `alembic check` is a cheap drift guard; async `env.py` matches the runtime stack | Enum changes must be hand-written; post-write hooks needed to keep revisions lint-clean |
| **Constraints and indexes** | Composite PK blocks duplicate memberships; `RESTRICT` protects tasks; `SET NULL` preserves them; composite indexes back the list and overdue queries | Rigidity: a team with tasks is protected rather than silently emptied, and deletion must be handled explicitly |
| **Append-only task events** | History is a first-class resource, and "completed"/"overdue" have a natural place to be recorded | Roughly doubles writes per mutation; ordering within a transaction is not defined by `created_at` alone; unbounded growth |
| **Overdue sweep as a lifespan task** | No broker, no extra deployment unit, no scheduler dependency; shuts down cleanly with the app | Bound to the web process — stops when the app stops, runs once per worker, no locking |
| **Tests against the real app and database** | Exercises routing, authorization, SQL, and serialisation rather than mocks; rollback gives isolation without truncation | Requires a live database and is slower; no in-memory substitute due to PostgreSQL-specific types |
| **Ruff** | One tool for lint and format, explicit rule set (`E`, `F`, `I`, `B`, `UP`), modern syntax enforced | Opinionated; some rules (like `B008`) need per-file configuration |

---

## Known Limitations

**Intentionally out of scope**

- No refresh tokens, logout, or revocation — access tokens are the only credential.
- No pagination, filtering, or sorting; list endpoints return everything with fixed ordering (tasks by `created_at` desc; teams/members by name and `joined_at` asc; events by `created_at` asc).
- No rate limiting or brute-force protection on `POST /auth/login`.
- No password reset, email verification, or account self-deletion; no user-deletion endpoint, so the `RESTRICT`/`SET NULL` behaviour is unreachable through the API.
- No comments, attachments, or labels on tasks, and no endpoint that edits or deletes an event — the audit log is append-only by design.

**Behavioural limitations**

- **Nullable fields cannot be cleared.** Every `PATCH /tasks/{task_id}` field applies only when non-`None`, and an omitted field is indistinguishable from an explicit `null`, so a task cannot be unassigned and `description`/`due_at` cannot be reset. Same for `description` on `PATCH /teams/{team_id}`.
- **Removing a member does not unassign their tasks** — `assignee_id` references `users`, not `team_members`, and the membership check runs only at assignment time.
- **Status transitions are unrestricted**, `OVERDUE` included, with no validation.
- **No optimistic concurrency** — simultaneous updates are last-write-wins.
- **Event ordering within a transaction is not guaranteed** by `created_at` alone, because PostgreSQL's `now()` is the transaction timestamp.
- **Emails are case-sensitive** — `User@example.com` and `user@example.com` are separate accounts.
- **`409` for a missing user when adding a team member** — `add_member` raises `ValueError` and the route maps all of them to `409`, where `404` would be more precise.
- **SSL is unconditional** — `connect_args={"ssl": True}` is hardcoded, so a non-TLS PostgreSQL needs a code change.
- **Overdue detection is bounded by its interval** — up to five minutes late, and only while the app runs.
- **Two migrations add the same enum values** (`e36b114e6120`, `09a1d1e26b7d`); both use `IF NOT EXISTS`, so they are safe but the second is redundant.
- **Duplicated `UserResponse`** in `app/schemas/auth.py` (`EmailStr`) and `app/schemas/user.py` (`str`).
- **Unused settings** — `app_name`, `app_version`, `app_env` are accepted but read nowhere.

**Test suite** — requires a live PostgreSQL database (`TEST_DATABASE_URL`); there is no containerized or in-memory database. Coverage focuses on authentication, authorization, the task lifecycle, and overdue processing; there are no pagination, concurrency, or load tests, and no test for the assignment-time-only assignee rule.

---

## Possible Future Improvements

None of this is implemented.

- Pagination, filtering, and sorting on list endpoints (status, priority, assignee, due-date ranges).
- Refresh tokens with rotation and revocation, or a token denylist.
- Move the overdue sweep to a dedicated worker or scheduled job, with a single-runner guarantee such as a PostgreSQL advisory lock.
- Validate status transitions; decide whether `OVERDUE` stays stored or becomes a recomputed flag.
- Optimistic concurrency via a version column on `tasks`.
- Unassign or re-validate tasks when a member leaves a team.
- Let nullable fields be cleared on `PATCH` by distinguishing omitted from explicit `null` (e.g. `model_fields_set`).
- Richer task workflow: tags, comments, attachments, sub-tasks, history filtering by event type.
- Observability: structured logging with request IDs, metrics, tracing, and separate liveness/readiness probes.
- Rate limiting and login throttling; CI running Ruff and pytest against a PostgreSQL service container.
- API versioning (e.g. `/api/v1`); email verification and password reset; consolidating the duplicated `UserResponse` and the redundant enum migration.

---

## Project Structure

```text
Assignment/
├── app/
│   ├── main.py               # app creation, lifespan (starts the scheduler), health, routers
│   ├── api/
│   │   ├── deps.py           # HTTPBearer scheme + get_current_user
│   │   └── routes/           # auth.py, users.py, teams.py, tasks.py
│   ├── core/                 # config, database, security, authorization (3 modules)
│   ├── models/               # base mixins + user, team, team_member, task, task_event
│   ├── schemas/              # Pydantic request/response models
│   └── services/             # auth, users, team, task, task_scheduler
├── docs/engineering-details.md   # Alembic revision history, per-file test breakdown
├── migrations/               # async env.py, script.py.mako, six revisions
├── scripts/create_admin.py   # interactive admin bootstrap
├── tests/                    # conftest.py + seven test modules
├── alembic.ini               # Alembic config + Ruff post-write hooks
├── pyproject.toml            # metadata, dependencies, dev extra, Ruff and pytest config
├── requirements.txt          # pinned mirror of the dependency set
├── .env.example              # template for required environment variables
├── Dockerfile                # python:3.12-slim image; installs the project, runs Uvicorn
├── docker-compose.yml        # single api service reading .env
└── .dockerignore             # keeps .venv, .git, and caches out of the build context
```

`app/models/__init__.py` aggregates every model so Alembic sees the full metadata. `scripts/__init__.py` makes the bootstrap runnable via `python -m`. Remaining package `__init__.py` files are empty markers. Generated paths (`__pycache__/`, `.venv/`, `build/`, caches) are omitted and covered by `.gitignore`.

---

## AI Usage Disclosure

AI coding tools were used during the development of this project, for implementation and refactoring (models, schemas, services, routes), debugging runtime errors from Alembic, SQLAlchemy async, and asyncpg, resolving Ruff lint and import-cycle issues, developing and adjusting the test suite and its shared fixtures, and drafting this README.

All AI-assisted changes were reviewed and validated against the running application: migrations were applied, the test suite was executed (58 passing tests), and the linters were run (`ruff check`, `ruff format --check`). The architecture, domain rules, and scope decisions follow the assignment requirements, and the code in this repository remains the authoritative description of the system's behaviour.
