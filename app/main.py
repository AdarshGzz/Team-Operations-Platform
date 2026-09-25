from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.routes.auth import router as auth_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.teams import router as teams_router
from app.api.routes.users import router as users_router
from app.services.task_scheduler import (
    start_overdue_task_scheduler,
    stop_overdue_task_scheduler,
)


def lifespan(app: FastAPI):
    start_overdue_task_scheduler()

    try:
        yield
    finally:
        stop_overdue_task_scheduler()


app = FastAPI(
    title="Team Operation Platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check(
    db: Session = Depends(get_db_session),
) -> dict[str, str]:
    db.execute(text("SELECT 1"))

    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
app.include_router(tasks_router)
