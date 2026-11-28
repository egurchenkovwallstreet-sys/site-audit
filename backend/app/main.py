from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text, update

from app.api.scans import router as scans_router
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.config import get_settings
from app.db.session import async_session_factory
from app.models.entities import Scan, ScanStatus
from app.services.scan_stale import reconcile_stale_scan

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.api.scans import _run_scan_task
    from app.services.scan_dispatch import bootstrap_queue_after_startup

    async with async_session_factory() as session:
        result = await session.execute(
            select(Scan).where(
                Scan.status.in_(
                    [ScanStatus.PENDING.value, ScanStatus.RUNNING.value]
                )
            )
        )
        for scan in result.scalars():
            await reconcile_stale_scan(session, scan)
            await session.refresh(scan)
        await session.execute(
            update(Scan)
            .where(Scan.status == ScanStatus.PENDING.value)
            .values(status=ScanStatus.QUEUED.value)
        )
        await session.commit()

    await bootstrap_queue_after_startup(_run_scan_task)
    yield


app = FastAPI(
    title="Site Audit API",
    description="API сервиса технического и комплаенс-аудита сайтов.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(scans_router)


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
