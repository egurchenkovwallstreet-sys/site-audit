from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import Finding, Scan, ScanStatus


def _scan_age_sec(scan: Scan, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    created = scan.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (now - created).total_seconds()


def scan_wall_clock_max_sec() -> float:
    settings = get_settings()
    return float(
        settings.scan_time_budget_sec
        + settings.scan_time_extension_sec
        + settings.scan_task_timeout_buffer_sec * 2
    )


def stale_after_sec() -> float:
    return scan_wall_clock_max_sec() + 180.0


def scan_task_timeout_sec() -> float:
    settings = get_settings()
    return float(settings.scan_time_budget_sec + settings.scan_task_timeout_buffer_sec)


async def mark_scan_failed(
    session: AsyncSession,
    scan: Scan,
    *,
    reason: str,
) -> None:
    scan.status = ScanStatus.FAILED.value
    scan.completed_at = datetime.now(timezone.utc)
    payload: dict = {"scan_failed_reason": reason}
    if scan.context_json:
        try:
            payload = {**json.loads(scan.context_json), **payload}
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    scan.context_json = json.dumps(payload, ensure_ascii=False)
    await session.commit()


async def requeue_scan_after_timeout(
    session: AsyncSession,
    scan: Scan,
) -> None:
    """Устаревший путь: мягкий requeue без удаления findings."""
    scan.status = ScanStatus.QUEUED.value
    scan.completed_at = None
    await session.commit()
    await session.refresh(scan)


async def reconcile_stale_scan(session: AsyncSession, scan: Scan) -> bool:
    """Зависший скан: продление / диагностика / requeue."""
    if scan.status not in (ScanStatus.PENDING.value, ScanStatus.RUNNING.value):
        return False
    if _scan_age_sec(scan) < stale_after_sec():
        return False
    from app.services.scan_finish import handle_wall_clock_timeout

    outcome = await handle_wall_clock_timeout(session, scan)
    return outcome in ("requeue_phase2", "requeue", "partial_done")


async def restart_scan(
    session: AsyncSession,
    scan: Scan,
) -> Scan:
    if scan.status == ScanStatus.COMPLETED.value:
        raise ValueError("completed")
    await session.execute(delete(Finding).where(Finding.scan_id == scan.id))
    scan.status = ScanStatus.QUEUED.value
    scan.context_json = None
    scan.completed_at = None
    await session.commit()
    await session.refresh(scan)
    return scan