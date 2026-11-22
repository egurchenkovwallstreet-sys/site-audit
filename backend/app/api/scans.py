from __future__ import annotations

import json
import time

from email.message import EmailMessage
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.checker import validate_target_url
from app.compliance.penalty_totals import sum_breach_penalties, sum_compliance_penalties
from app.config import get_settings
from app.db.session import async_session_factory, get_db
from app.models.entities import Finding, Scan, ScanStatus
from app.outreach.email_preview import build_outreach_email_text
from app.services.scan_runner import run_compliance_scan
from app.services.smtp_send import (
    SmtpDeliveryError,
    SmtpNotConfiguredError,
    send_email_message,
    smtp_is_configured,
)

router = APIRouter(prefix="/api/scans", tags=["scans"])

_SEND_PREVIEW_COOLDOWN_SEC = 90.0
_last_preview_send_at: dict[int, float] = {}


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


class SendPreviewEmailRequest(BaseModel):
    to_email: EmailStr


class SendPreviewEmailResponse(BaseModel):
    ok: bool
    to: str
    subject: str


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


def _contact_emails_from_scan(scan: Scan) -> list[str]:
    if not scan.context_json:
        return []
    try:
        raw = json.loads(scan.context_json)
        emails = raw.get("contact_emails") or []
        return [str(e).strip().lower() for e in emails if e]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


@router.post("/{scan_id}/send-preview-email", response_model=SendPreviewEmailResponse)
async def send_preview_email(
    scan_id: int,
    body: SendPreviewEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> SendPreviewEmailResponse:
    if not smtp_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Отправка не настроена: укажите SMTP_HOST, SMTP_USER и SMTP_PASSWORD в .env на сервере.",
        )

    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    if scan.status != ScanStatus.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail="Письмо можно отправить только после завершения проверки.",
        )

    allowed = _contact_emails_from_scan(scan)
    to_norm = body.to_email.strip().lower()
    if to_norm not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Можно отправить только на адрес из списка найденных на сайте.",
        )

    now = time.monotonic()
    last = _last_preview_send_at.get(scan_id, 0.0)
    if now - last < _SEND_PREVIEW_COOLDOWN_SEC:
        raise HTTPException(
            status_code=429,
            detail="Подождите минуту перед повторной отправкой с этого скана.",
        )

    result = await session.execute(select(Finding).where(Finding.scan_id == scan_id))
    findings = result.scalars().all()
    compliance_total = sum_compliance_penalties(findings)
    breach_total = sum_breach_penalties(findings)

    settings = get_settings()
    landing = settings.public_site_url.rstrip("/")
    if "?" in landing:
        landing += "&utm_source=outreach&utm_medium=email"
    else:
        landing += "/?utm_source=outreach&utm_medium=email"

    subject, text_body = build_outreach_email_text(
        target_url=scan.target_url,
        compliance_total=compliance_total,
        breach_total=breach_total,
        landing_url=landing,
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = to_norm
    message.set_content(text_body, charset="utf-8")

    try:
        await send_email_message(message)
    except SmtpNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SmtpDeliveryError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SMTP не принял письмо: {exc}",
        ) from exc

    _last_preview_send_at[scan_id] = now
    return SendPreviewEmailResponse(ok=True, to=to_norm, subject=subject)