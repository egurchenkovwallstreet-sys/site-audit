from __future__ import annotations

import asyncio
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import async_session_factory
from app.models.entities import Scan, ScanStatus

_slots_in_use = 0
_dispatch_lock = asyncio.Lock()


def slots_in_use() -> int:
    return _slots_in_use


def set_slots_in_use(value: int) -> None:
    global _slots_in_use
    _slots_in_use = max(0, value)


async def count_scans_by_status(session: AsyncSession, status: str) -> int:
    q = await session.execute(
        select(func.count()).select_from(Scan).where(Scan.status == status)
    )
    return int(q.scalar_one())


async def queue_waiting_ahead(session: AsyncSession, scan: Scan) -> int:
    if scan.status != ScanStatus.QUEUED.value:
        return 0
    created = scan.created_at
    q = await session.execute(
        select(func.count())
        .select_from(Scan)
        .where(
            Scan.status == ScanStatus.QUEUED.value,
            Scan.created_at < created,
        )
    )
    return int(q.scalar_one())


def estimate_wait_sec(*, waiting_ahead: int, running_count: int) -> int:
    """Оценка до старта/готовности: ~5 проверок за 10 мин при 2 активных (внутр.)."""
    scans_per_10_min = 5
    bucket_sec = 600
    position = waiting_ahead + 1 + max(0, running_count)
    if position <= 0:
        return bucket_sec
    batches = math.ceil(position / scans_per_10_min)
    return max(bucket_sec, batches * bucket_sec)


async def queue_metrics(session: AsyncSession, scan: Scan) -> tuple[int, int | None]:
    ahead = await queue_waiting_ahead(session, scan)
    if scan.status != ScanStatus.QUEUED.value:
        return 0, None
    running = await count_scans_by_status(session, ScanStatus.RUNNING.value)
    eta = estimate_wait_sec(waiting_ahead=ahead, running_count=running)
    return ahead, eta


async def _oldest_queued(session: AsyncSession) -> Scan | None:
    q = await session.execute(
        select(Scan)
        .where(Scan.status == ScanStatus.QUEUED.value)
        .order_by(Scan.created_at.asc())
        .limit(1)
    )
    return q.scalar_one_or_none()


async def fill_scan_slots(run_fn) -> list[int]:
    from app.services.scan_dispatch import launch_scan_worker

    settings = get_settings()
    max_slots = settings.scan_queue_max_concurrent
    started: list[int] = []

    async with _dispatch_lock:
        while _slots_in_use < max_slots:
            async with async_session_factory() as session:
                scan = await _oldest_queued(session)
                if scan is None:
                    break
                scan_id = scan.id
            _slots_in_use += 1
            launch_scan_worker(scan_id, run_fn)
            started.append(scan_id)
    return started


async def decrement_slot() -> None:
    global _slots_in_use
    async with _dispatch_lock:
        _slots_in_use = max(0, _slots_in_use - 1)


async def enqueue_and_try_start(run_fn) -> None:
    await fill_scan_slots(run_fn)