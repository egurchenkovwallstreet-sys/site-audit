from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.checker import validate_target_url
from app.db.session import async_session_factory, get_db
from app.models.entities import Finding, Scan, ScanStatus
from app.services.scan_runner import run_compliance_scan

router = APIRouter(prefix="/api/scans", tags=["scans"])


class ScanCreateRequest(BaseModel):
    target_url: str = Field(..., min_length=8, max_length=2048)


class ScanContext(BaseModel):
    scope: str | None = None
    privacy_found: bool | None = None
    privacy_source: str | None = None
    consent_found: bool | None = None
    consent_source: str | None = None
    requested_url: str | None = None
    scanned_url: str | None = None
    used_fallback: bool | None = None
    tried_urls: list[str] | None = None
    scanned_urls: list[str] | None = None
    pages_checked: int | None = None
    contact_emails: list[str] | None = None


class ScanResponse(BaseModel):
    id: int
    target_url: str
    status: str
    context: ScanContext | None = None


class FindingResponse(BaseModel):
    id: int
    type: str
    severity: str
    title: str
    description: str
    legal_article: str | None
    max_penalty: int | None
    color: str | None
    min_level: int
    remediation: str | None


async def _run_scan_task(scan_id: int) -> None:
    async with async_session_factory() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None:
            return
        try:
            await run_compliance_scan(session, scan)
        except Exception:
            await session.rollback()


@router.post("", response_model=ScanResponse)
async def create_scan(
    body: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> ScanResponse:
    try:
        target = validate_target_url(body.target_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scan = Scan(target_url=target, status=ScanStatus.PENDING.value)
    session.add(scan)
    await session.commit()
    await session.refresh(scan)

    background_tasks.add_task(_run_scan_task, scan.id)

    return _scan_response(scan)


def _scan_response(scan: Scan) -> ScanResponse:
    ctx: ScanContext | None = None
    if scan.context_json:
        try:
            raw = json.loads(scan.context_json)
            ctx = ScanContext(**raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            ctx = None
    return ScanResponse(
        id=scan.id,
        target_url=scan.target_url,
        status=scan.status,
        context=ctx,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: int, session: AsyncSession = Depends(get_db)) -> ScanResponse:
    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    return _scan_response(scan)


@router.get("/{scan_id}/findings", response_model=list[FindingResponse])
async def get_scan_findings(
    scan_id: int, session: AsyncSession = Depends(get_db)
) -> list[FindingResponse]:
    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")

    result = await session.execute(
        select(Finding).where(Finding.scan_id == scan_id).order_by(Finding.id)
    )
    findings = result.scalars().all()
    return [
        FindingResponse(
            id=f.id,
            type=f.type,
            severity=f.severity,
            title=f.title,
            description=f.description,
            legal_article=f.legal_article,
            max_penalty=f.max_penalty,
            color=f.color,
            min_level=f.min_level,
            remediation=f.remediation,
        )
        for f in findings
    ]