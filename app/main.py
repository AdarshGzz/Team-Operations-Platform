from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import AsyncSession

app = FastAPI(
    title="Team Operation Platform",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    async with AsyncSession() as session:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}
