from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Finding, Scan, ScanStatus


async def requeue_interrupted_running_scans(session: AsyncSession) -> int:
    """После перезапуска backend воркеров нет — running в БД переводим в очередь."""
    result = await session.execute(
        select(Scan).where(Scan.status == ScanStatus.RUNNING.value)
    )
    scans = list(result.scalars())
    if not scans:
        return 0

    for scan in scans:
        await session.execute(delete(Finding).where(Finding.scan_id == scan.id))
        scan.status = ScanStatus.QUEUED.value
        scan.context_json = None
        scan.completed_at = None

    await session.commit()
    return len(scans)