from __future__ import annotations

import json
import time

from email.message import EmailMessage
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.checker import validate_target_url
from app.data.koap_sanctions import sanctions_for_penalty_code
from app.db.session import async_session_factory, get_db
from app.models.entities import Finding, Scan, ScanStatus
from app.services.outreach_message import (
    compose_outreach_letter,
    outreach_delivery_meta,
)
from app.reports.compose import compose_extended_report, compose_short_report
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
    test_inbox_url: str | None = None


class OutreachEmailPreviewResponse(BaseModel):
    to: str
    subject: str
    body: str
    can_send: bool
    test_inbox_url: str | None = None


class PaidReportResponse(BaseModel):
    variant: str
    markdown: str
    disclaimer: str = (
        "Ориентиры по КоАП, не юридическая консультация. "
        "Полная выдача — после оплаты тарифа (фаза B)."
    )


class PenaltySanctionsResponse(BaseModel):
    koap_part: str
    koap_repeat_part: str | None = None
    ip_max: int
    legal_max: int
    ip_repeat_max: int | None = None
    legal_repeat_max: int | None = None
    ip_note: str | None = None


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
    penalty_code: str | None = None
    sanctions: PenaltySanctionsResponse | None = None


def _sanctions_response(penalty_code: str | None) -> PenaltySanctionsResponse | None:
    limits = sanctions_for_penalty_code(penalty_code)
    if limits is None:
        return None
    return PenaltySanctionsResponse(
        koap_part=limits.koap_part,
        koap_repeat_part=limits.koap_repeat_part,
        ip_max=limits.ip_max,
        legal_max=limits.legal_max,
        ip_repeat_max=limits.ip_repeat_max,
        legal_repeat_max=limits.legal_repeat_max,
        ip_note=limits.ip_note,
    )


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
            penalty_code=f.penalty_code,
            sanctions=_sanctions_response(f.penalty_code),
        )
        for f in findings
    ]


async def _scan_findings(session: AsyncSession, scan_id: int) -> list[Finding]:
    result = await session.execute(
        select(Finding).where(Finding.scan_id == scan_id).order_by(Finding.id)
    )
    return list(result.scalars().all())


def _validate_outreach_recipient(scan: Scan, to_email: str) -> str:
    if scan.status != ScanStatus.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail="Доступно только после завершения проверки.",
        )
    allowed = _contact_emails_from_scan(scan)
    to_norm = to_email.strip().lower()
    if to_norm not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Можно только на адрес из списка найденных на сайте.",
        )
    return to_norm


def _contact_emails_from_scan(scan: Scan) -> list[str]:
    if not scan.context_json:
        return []
    try:
        raw = json.loads(scan.context_json)
        emails = raw.get("contact_emails") or []
        return [str(e).strip().lower() for e in emails if e]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


@router.get("/{scan_id}/paid-report", response_model=PaidReportResponse)
async def paid_report_preview(
    scan_id: int,
    variant: str = "short",
    session: AsyncSession = Depends(get_db),
) -> PaidReportResponse:
    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    if scan.status != ScanStatus.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail="Отчёт доступен после завершения проверки.",
        )
    if variant not in ("short", "extended"):
        raise HTTPException(
            status_code=400,
            detail="variant должен быть short или extended",
        )
    findings = await _scan_findings(session, scan_id)
    markdown = (
        compose_extended_report(scan, findings)
        if variant == "extended"
        else compose_short_report(scan, findings)
    )
    return PaidReportResponse(variant=variant, markdown=markdown)


@router.get("/{scan_id}/outreach-email-preview", response_model=OutreachEmailPreviewResponse)
async def outreach_email_preview(
    scan_id: int,
    to_email: EmailStr,
    session: AsyncSession = Depends(get_db),
) -> OutreachEmailPreviewResponse:
    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    to_norm = _validate_outreach_recipient(scan, str(to_email))
    findings = await _scan_findings(session, scan_id)
    subject, body = compose_outreach_letter(scan, findings)
    meta = outreach_delivery_meta()
    return OutreachEmailPreviewResponse(
        to=to_norm,
        subject=subject,
        body=body,
        can_send=bool(meta["can_send"]),
        test_inbox_url=meta.get("test_inbox_url"),  # type: ignore[arg-type]
    )


@router.post("/{scan_id}/send-preview-email", response_model=SendPreviewEmailResponse)
async def send_preview_email(
    scan_id: int,
    body: SendPreviewEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> SendPreviewEmailResponse:
    if not smtp_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Отправка не настроена: включите Mailpit или SMTP (см. docs/smtp-setup.md).",
        )

    scan = await session.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    to_norm = _validate_outreach_recipient(scan, str(body.to_email))

    now = time.monotonic()
    last = _last_preview_send_at.get(scan_id, 0.0)
    if now - last < _SEND_PREVIEW_COOLDOWN_SEC:
        raise HTTPException(
            status_code=429,
            detail="Подождите минуту перед повторной отправкой с этого скана.",
        )

    findings = await _scan_findings(session, scan_id)
    subject, text_body = compose_outreach_letter(scan, findings)

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
    meta = outreach_delivery_meta()
    inbox = meta.get("test_inbox_url")
    return SendPreviewEmailResponse(
        ok=True,
        to=to_norm,
        subject=subject,
        test_inbox_url=inbox if isinstance(inbox, str) else None,
    )