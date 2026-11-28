from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AdminIncident, Finding, Scan


async def count_findings(session: AsyncSession, scan_id: int) -> int:
    q = await session.execute(
        select(func.count()).select_from(Finding).where(Finding.scan_id == scan_id)
    )
    return int(q.scalar_one())


def classify_exception(exc: BaseException) -> str:
    """our | site | unknown"""
    msg = str(exc).lower()
    if isinstance(exc, (MemoryError, asyncio.TimeoutError)):
        return "our"
    if "playwright" in msg or "nuclei" in msg:
        return "our"
    if "connection" in msg or "timeout" in msg or "ssl" in msg:
        return "site"
    return "unknown"


async def create_admin_incident(
    session: AsyncSession,
    *,
    scan: Scan,
    kind: str,
    severity: str,
    title: str,
    detail: dict[str, Any],
) -> AdminIncident:
    row = AdminIncident(
        scan_id=scan.id,
        kind=kind,
        severity=severity,
        title=title,
        target_url=scan.target_url,
        detail_json=json.dumps(detail, ensure_ascii=False),
        resolved=False,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


def slow_scan_diagnosis(
    *,
    pages_checked: int | None,
    findings_count: int,
    phase: int,
    partial_html: bool,
) -> dict[str, Any]:
    causes: list[str] = []
    if pages_checked is not None and pages_checked >= 15:
        causes.append("Много страниц или тяжёлый обход сайта.")
    if not partial_html:
        causes.append(
            "Содержимое страниц почти не читалось (антибот, блокировка, медленный отклик)."
        )
    if findings_count == 0 and not causes:
        causes.append(
            "Не удалось собрать данные за 20 минут — возможно, сайт очень медленный или недоступен."
        )
    if phase >= 2:
        causes.append("Использовано продление +10 мин (вторая фаза).")

    can_deliver = findings_count > 0
    return {
        "pages_checked": pages_checked,
        "findings_count": findings_count,
        "likely_causes": causes,
        "can_deliver_partial_result": can_deliver,
        "site_checkable": can_deliver or partial_html or (pages_checked or 0) > 0,
    }


def exception_detail(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc)[:2000],
        "traceback": traceback.format_exc()[-4000:],
    }