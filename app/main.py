import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.routes.auth import router as auth_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.teams import router as teams_router
from app.api.routes.users import router as users_router
from app.services.task_scheduler import overdue_task_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(overdue_task_scheduler())

    try:
        yield
    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Team Operation Platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def database_health_check(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    await db.execute(text("SELECT 1"))

    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
app.include_router(tasks_router)
