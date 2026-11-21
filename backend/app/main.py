from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.db.session import async_session_factory

settings = get_settings()

app = FastAPI(
    title="Site Audit API",
    description="API сервиса технического и комплаенс-аудита сайтов.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "site-audit-api", "status": "ready"}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db() -> dict[str, str]:
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
