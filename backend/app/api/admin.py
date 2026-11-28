from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.admin_auth import (
    admin_configured,
    clear_admin_session,
    issue_admin_session,
    require_admin,
    verify_login,
)
from app.services.admin_incidents import (
    backfill_failed_scans,
    list_admin_incidents,
    resolve_admin_incident,
)
from app.services.admin_stats import PeriodKey, build_admin_stats
from app.services.queue_snapshot import (
    list_queue_snapshots,
    period_since,
    read_live_queue_counts,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)


class AdminLoginResponse(BaseModel):
    ok: bool
    email: str


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    body: AdminLoginRequest,
    response: Response,
) -> AdminLoginResponse:
    if not admin_configured():
        raise HTTPException(
            status_code=503,
            detail="Админ-кабинет не настроен (ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_SESSION_SECRET).",
        )
    if not verify_login(body.email, body.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    issue_admin_session(response, body.email)
    return AdminLoginResponse(ok=True, email=body.email.lower())


@router.post("/logout")
async def admin_logout(response: Response) -> dict[str, bool]:
    clear_admin_session(response)
    return {"ok": True}


@router.get("/me")
async def admin_me(email: str = Depends(require_admin)) -> dict[str, str]:
    return {"email": email}


@router.get("/stats")
async def admin_stats(
    period: PeriodKey = "day",
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await build_admin_stats(session, period)


@router.get("/stats/all-periods")
async def admin_stats_all(
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key in ("day", "week", "month", "all"):
        out[key] = await build_admin_stats(session, key)  # type: ignore[arg-type]
    return out


@router.get("/incidents")
async def admin_incidents_list(
    limit: int = 40,
    unresolved_only: bool = True,
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, list]:
    items = await list_admin_incidents(
        session, limit=min(max(limit, 1), 100), unresolved_only=unresolved_only
    )
    return {"items": items}


@router.post("/incidents/backfill-failed")
async def admin_incidents_backfill(
    limit: int = 30,
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    n = await backfill_failed_scans(session, limit=min(max(limit, 1), 100))
    return {"created": n}


@router.post("/incidents/{incident_id}/resolve")
async def admin_incidents_resolve(
    incident_id: int,
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    row = await resolve_admin_incident(session, incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return row


@router.get("/queue/live")
async def admin_queue_live(
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await read_live_queue_counts(session)


@router.get("/queue/history")
async def admin_queue_history(
    period: PeriodKey = "day",
    limit: int = 200,
    high_load_only: bool = False,
    _email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from app.config import get_settings

    settings = get_settings()
    since = period_since(period)
    items = await list_queue_snapshots(
        session,
        since=since,
        limit=limit,
        high_load_only=high_load_only,
        threshold=settings.scan_queue_alert_min_waiting,
    )
    return {"period": period, "items": items}