from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.teams import router as teams_router
from app.api.routes.users import router as users_router
from app.core.database import AsyncSessionLocal

app = FastAPI(
    title="Team Operation Platform",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
