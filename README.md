# Team Operations Platform

FastAPI backend for managing users, teams, and tasks, with role-based access
control and an append-only audit trail of task events.

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async) with asyncpg
- PostgreSQL
- Alembic migrations
- Pydantic v2 and pydantic-settings
- PyJWT and pwdlib (Argon2) for authentication

## Requirements

- Python 3.12 - 3.14
- A PostgreSQL database

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Then set `DATABASE_URL` (use the `postgresql+asyncpg://` scheme) and a long
random `JWT_SECRET_KEY` in `.env`, and apply the migrations:

```bash
alembic upgrade head
```

## Running

```bash
uvicorn app.main:app --reload
```

Interactive docs are served at http://localhost:8000/docs.

The first admin account can be created with:

```bash
python -m scripts.create_admin
```

## Tests

```bash
pytest
```

Tests run against the database in `TEST_DATABASE_URL`, each inside a
transaction that is rolled back afterwards. Copy `.env.example` to `.env` and
point `TEST_DATABASE_URL` at a database you do not mind writing to.

## Roles

| Role | Access |
| --- | --- |
| `ADMIN` | Full access to every team, task, and user |
| `MANAGER` | Manages teams they belong to |
| `MEMBER` | Sees their teams, and can modify only tasks assigned to them |

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/register` | Register a new member |
| `POST` | `/auth/login` | Exchange credentials for a JWT |
| `GET` | `/users/me` | The authenticated user |
| `GET` | `/users` | List users (admin) |
| `GET` `PATCH` | `/users/{user_id}` | Read or update a user (admin) |
| `GET` `POST` | `/teams` | List accessible teams, or create one (admin) |
| `GET` `PATCH` `DELETE` | `/teams/{team_id}` | Read, rename, or delete a team |
| `GET` `POST` `DELETE` | `/teams/{team_id}/members` | Manage team membership |
| `GET` `POST` | `/teams/{team_id}/tasks` | List or create a team's tasks |
| `GET` `PATCH` `DELETE` | `/tasks/{task_id}` | Read, update, or delete a task |
| `PATCH` | `/tasks/{task_id}/status` | Change task status |
| `GET` | `/tasks/{task_id}/events` | The task's audit trail |
| `GET` | `/health` `/health/db` | Liveness and database connectivity |

## Task events

Creating, updating, reassigning, and completing a task each append a row to
`task_events` recording the change, giving every task a full audit trail. A
background scheduler marks past-due tasks as `OVERDUE` every five minutes.

## Docker

```bash
docker compose up --build
```

The API reads its configuration from `.env`, which `docker-compose.yml`
passes into the container.
