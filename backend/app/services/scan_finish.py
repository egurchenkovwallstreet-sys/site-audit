from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import Finding, Scan, ScanStatus
from app.services.scan_incidents import (
    create_admin_incident,
    count_findings,
    slow_scan_diagnosis,
)
from app.services.scan_run_meta import (
    bump_auto_retry,
    bump_to_phase2,
    read_context,
    read_run_meta,
    write_context,
)
from app.services.scan_stale import mark_scan_failed


async def requeue_phase2_extension(
    session: AsyncSession,
    scan: Scan,
) -> None:
    """+10 мин: в очередь без сброса findings (если были)."""
    bump_to_phase2(scan)
    scan.status = ScanStatus.QUEUED.value
    scan.completed_at = None
    await session.commit()
    await session.refresh(scan)


async def requeue_auto_retry(
    session: AsyncSession,
    scan: Scan,
    *,
    reason: str,
) -> int:
    bump_auto_retry(scan)
    ctx = read_context(scan)
    ctx["auto_retry_reason"] = reason
    write_context(scan, ctx)
    scan.status = ScanStatus.QUEUED.value
    scan.completed_at = None
    await session.commit()
    await session.refresh(scan)
    meta = read_run_meta(scan)
    return int(meta["auto_retries"])


async def complete_partial_if_possible(
    session: AsyncSession,
    scan: Scan,
    *,
    note: str,
) -> bool:
    n = await count_findings(session, scan.id)
    if n <= 0:
        return False
    ctx = read_context(scan)
    ctx["partial_scan"] = True
    scope = ctx.get("scope") or ""
    ctx["scope"] = f"{scope} {note}".strip()
    write_context(scan, ctx)
    scan.status = ScanStatus.COMPLETED.value
    scan.completed_at = datetime.now(timezone.utc)
    await session.commit()
    return True


async def handle_wall_clock_timeout(
    session: AsyncSession,
    scan: Scan,
) -> str:
    """
    Возвращает: requeue_phase2 | requeue | partial_done | failed | none
    """
    meta = read_run_meta(scan)
    if scan.status in (ScanStatus.COMPLETED.value, ScanStatus.FAILED.value):
        return "none"

    if meta["phase"] < 2 and not meta["extension_used"]:
        await requeue_phase2_extension(session, scan)
        return "requeue_phase2"

    ctx = read_context(scan)
    pages = ctx.get("pages_checked")
    if isinstance(pages, str):
        try:
            pages = int(pages)
        except ValueError:
            pages = None
    findings_n = await count_findings(session, scan.id)
    diagnosis = slow_scan_diagnosis(
        pages_checked=pages if isinstance(pages, int) else None,
        findings_count=findings_n,
        phase=meta["phase"],
        partial_html=bool(ctx.get("privacy_found") is not None or ctx.get("scanned_urls")),
    )

    if await complete_partial_if_possible(
        session,
        scan,
        note="Частичный результат: лимит 20 минут исчерпан, показано то, что успели собрать.",
    ):
        await create_admin_incident(
            session,
            scan=scan,
            kind="slow_scan_partial_ok",
            severity="info",
            title="Долгая проверка: выдан частичный результат клиенту",
            detail=diagnosis,
        )
        return "partial_done"

    await create_admin_incident(
        session,
        scan=scan,
        kind="slow_scan_no_result",
        severity="warn",
        title="Проверка не уложилась в 20 мин, результата нет",
        detail=diagnosis,
    )

    settings = get_settings()
    if meta["auto_retries"] < settings.scan_auto_retry_max:
        await requeue_auto_retry(
            session,
            scan,
            reason="slow_no_result_auto",
        )
        return "requeue"

    await mark_scan_failed(
        session,
        scan,
        reason=(
            "Сайт не удалось проверить за 20 минут. "
            "Причины смотрите в админ-кабинете; попробуйте перезапуск позже."
        ),
    )
    return "failed"