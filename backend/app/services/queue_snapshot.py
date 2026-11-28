from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import AdminIncident, QueueSnapshot, ScanStatus
from app.services.scan_queue import count_scans_by_status

logger = logging.getLogger(__name__)

PeriodKey = Literal["day", "week", "month", "all"]


def period_since(period: PeriodKey) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(hours=24)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    return None


async def read_live_queue_counts(session: AsyncSession) -> dict[str, int]:
    queued = await count_scans_by_status(session, ScanStatus.QUEUED.value)
    running = await count_scans_by_status(session, ScanStatus.RUNNING.value)
    settings = get_settings()
    return {
        "queued_now": queued,
        "running_now": running,
        "max_concurrent": settings.scan_queue_max_concurrent,
        "alert_threshold": settings.scan_queue_alert_min_waiting,
    }


async def record_queue_snapshot(session: AsyncSession) -> QueueSnapshot:
    live = await read_live_queue_counts(session)
    row = QueueSnapshot(
        queued_count=live["queued_now"],
        running_count=live["running_now"],
        max_concurrent=live["max_concurrent"],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def queue_max_waiting_in_period(
    session: AsyncSession,
    since: datetime | None,
) -> int:
    q = select(func.max(QueueSnapshot.queued_count))
    if since is not None:
        q = q.where(QueueSnapshot.recorded_at >= since)
    result = await session.execute(q)
    value = result.scalar_one()
    return int(value) if value is not None else 0


async def queue_high_load_episode_count(
    session: AsyncSession,
    since: datetime | None,
    *,
    threshold: int,
) -> int:
    q = (
        select(func.count())
        .select_from(QueueSnapshot)
        .where(QueueSnapshot.queued_count >= threshold)
    )
    if since is not None:
        q = q.where(QueueSnapshot.recorded_at >= since)
    result = await session.execute(q)
    return int(result.scalar_one())


async def list_queue_snapshots(
    session: AsyncSession,
    *,
    since: datetime | None,
    limit: int = 120,
    high_load_only: bool = False,
    threshold: int = 5,
) -> list[dict[str, Any]]:
    q = (
        select(QueueSnapshot)
        .order_by(QueueSnapshot.recorded_at.desc())
        .limit(min(max(limit, 1), 2000))
    )
    if since is not None:
        q = q.where(QueueSnapshot.recorded_at >= since)
    if high_load_only:
        q = q.where(QueueSnapshot.queued_count >= threshold)
    result = await session.execute(q)
    rows = list(result.scalars())
    return [
        {
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "queued_count": r.queued_count,
            "running_count": r.running_count,
            "max_concurrent": r.max_concurrent,
        }
        for r in rows
    ]


async def list_queue_peaks(
    session: AsyncSession,
    *,
    since: datetime | None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Снимки с максимальной очередью за период (топ по queued_count)."""
    q = select(QueueSnapshot).order_by(
        QueueSnapshot.queued_count.desc(),
        QueueSnapshot.recorded_at.desc(),
    )
    if since is not None:
        q = q.where(QueueSnapshot.recorded_at >= since)
    q = q.limit(min(max(limit, 1), 100))
    result = await session.execute(q)
    rows = list(result.scalars())
    return [
        {
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "queued_count": r.queued_count,
            "running_count": r.running_count,
            "max_concurrent": r.max_concurrent,
        }
        for r in rows
    ]


async def sync_queue_load_incident(session: AsyncSession, queued: int) -> None:
    settings = get_settings()
    threshold = settings.scan_queue_alert_min_waiting
    kind = "queue_high_load"

    open_q = await session.execute(
        select(AdminIncident)
        .where(
            AdminIncident.kind == kind,
            AdminIncident.resolved.is_(False),
        )
        .order_by(AdminIncident.created_at.desc())
        .limit(1)
    )
    open_row = open_q.scalar_one_or_none()

    if queued < threshold:
        if open_row is not None:
            open_row.resolved = True
            await session.commit()
        return

    detail = {
        "queued_count": queued,
        "threshold": threshold,
        "message": f"В очереди {queued} проверок (порог {threshold})",
    }
    title = f"Высокая очередь: {queued} сайтов ждут проверку"

    if open_row is not None:
        open_row.title = title
        open_row.target_url = "—"
        open_row.detail_json = json.dumps(detail, ensure_ascii=False)
        open_row.severity = "warn" if queued < threshold + 3 else "critical"
        await session.commit()
        return

    session.add(
        AdminIncident(
            scan_id=None,
            kind=kind,
            severity="warn" if queued < threshold + 3 else "critical",
            title=title,
            target_url="—",
            detail_json=json.dumps(detail, ensure_ascii=False),
            resolved=False,
        )
    )
    await session.commit()


async def queue_monitor_loop() -> None:
    settings = get_settings()
    interval = max(15, settings.scan_queue_snapshot_interval_sec)
    while True:
        try:
            from app.db.session import async_session_factory

            async with async_session_factory() as session:
                live = await read_live_queue_counts(session)
                await record_queue_snapshot(session)
                await sync_queue_load_incident(session, live["queued_now"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("queue_monitor_loop failed")
        await asyncio.sleep(interval)