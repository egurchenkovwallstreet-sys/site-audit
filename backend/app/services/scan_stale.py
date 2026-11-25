from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import Finding, Scan, ScanStatus


def _scan_age_sec(scan: Scan, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    created = scan.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (now - created).total_seconds()


def stale_after_sec() -> float:
    settings = get_settings()
    return float(settings.scan_time_budget_sec) + 180.0


def scan_task_timeout_sec() -> float:
    return stale_after_sec()


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


async def reconcile_stale_scan(session: AsyncSession, scan: Scan) -> bool:
    """Если скан завис в pending/running — пометить failed. Возврат: был ли сброшен."""
    if scan.status not in (ScanStatus.PENDING.value, ScanStatus.RUNNING.value):
        return False
    if _scan_age_sec(scan) < stale_after_sec():
        return False
    await mark_scan_failed(
        session,
        scan,
        reason="Превышено время ожидания (сервер не завершил проверку). "
        "Запустите проверку снова.",
    )
    return True


async def restart_scan(
    session: AsyncSession,
    scan: Scan,
) -> Scan:
    if scan.status == ScanStatus.COMPLETED.value:
        raise ValueError("completed")
    await session.execute(delete(Finding).where(Finding.scan_id == scan.id))
    scan.status = ScanStatus.PENDING.value
    scan.context_json = None
    scan.completed_at = None
    await session.commit()
    await session.refresh(scan)
    return scan