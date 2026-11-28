from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Finding, Scan, ScanStatus
from app.services.scan_run_meta import RUN_META_KEY, read_context, write_context


async def requeue_interrupted_running_scans(session: AsyncSession) -> int:
    """После перезапуска backend воркеров нет — running в БД переводим в очередь."""
    result = await session.execute(
        select(Scan).where(Scan.status == ScanStatus.RUNNING.value)
    )
    scans = list(result.scalars())
    if not scans:
        return 0

    for scan in scans:
        ctx = read_context(scan)
        run_meta = ctx.get(RUN_META_KEY)
        await session.execute(delete(Finding).where(Finding.scan_id == scan.id))
        scan.status = ScanStatus.QUEUED.value
        scan.completed_at = None
        if isinstance(run_meta, dict):
            new_ctx = {
                RUN_META_KEY: run_meta,
                "scan_recovery_note": "Перезапуск сервера; проверка снова в очереди.",
            }
            write_context(scan, new_ctx)
        else:
            scan.context_json = json.dumps(
                {
                    "scan_recovery_note": "Перезапуск сервера; проверка снова в очереди.",
                },
                ensure_ascii=False,
            )

    await session.commit()
    return len(scans)