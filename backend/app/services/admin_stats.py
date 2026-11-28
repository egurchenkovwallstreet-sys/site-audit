from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Finding, Scan, ScanStatus

PeriodKey = Literal["day", "week", "month", "all"]


def period_bounds(period: PeriodKey) -> tuple[datetime | None, datetime]:
    now = datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(hours=24), now
    if period == "week":
        return now - timedelta(days=7), now
    if period == "month":
        return now - timedelta(days=30), now
    return None, now


async def build_admin_stats(
    session: AsyncSession,
    period: PeriodKey,
) -> dict[str, Any]:
    since, until = period_bounds(period)
    scan_filter = []
    if since is not None:
        scan_filter.append(Scan.created_at >= since)

    async def count_scans(extra: list) -> int:
        q = await session.execute(
            select(func.count()).select_from(Scan).where(*scan_filter, *extra)
        )
        return int(q.scalar_one())

    created = await count_scans([])
    completed = await count_scans([Scan.status == ScanStatus.COMPLETED.value])
    failed = await count_scans([Scan.status == ScanStatus.FAILED.value])
    queued_period = await count_scans([Scan.status == ScanStatus.QUEUED.value])
    running_period = await count_scans([Scan.status == ScanStatus.RUNNING.value])

    q_now = await session.execute(
        select(func.count())
        .select_from(Scan)
        .where(Scan.status == ScanStatus.QUEUED.value)
    )
    r_now = await session.execute(
        select(func.count())
        .select_from(Scan)
        .where(Scan.status == ScanStatus.RUNNING.value)
    )
    queued_now = int(q_now.scalar_one())
    running_now = int(r_now.scalar_one())

    status_rows = await session.execute(
        select(Scan.status, func.count())
        .where(*scan_filter)
        .group_by(Scan.status)
        .order_by(Scan.status)
    )
    by_status = [
        {"status": row[0], "count": int(row[1])} for row in status_rows.fetchall()
    ]

    duration_q = await session.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Scan.completed_at - Scan.created_at,
                )
            )
        ).where(
            *scan_filter,
            Scan.status == ScanStatus.COMPLETED.value,
            Scan.completed_at.isnot(None),
        )
    )
    avg_sec = duration_q.scalar_one()
    avg_completion_sec = float(avg_sec) if avg_sec is not None else None

    ips_q = await session.execute(
        select(func.count(func.distinct(Scan.client_ip))).where(
            *scan_filter,
            Scan.client_ip.isnot(None),
        )
    )
    unique_ips = int(ips_q.scalar_one())

    top_targets = await session.execute(
        select(Scan.target_url, func.count())
        .where(*scan_filter)
        .group_by(Scan.target_url)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_urls = [
        {"url": row[0], "count": int(row[1])} for row in top_targets.fetchall()
    ]

    scan_time_filter = [Scan.created_at >= since] if since is not None else []

    f_total = await session.execute(
        select(func.count())
        .select_from(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .where(*scan_time_filter)
    )
    findings_total = int(f_total.scalar_one())

    f_by_type = await session.execute(
        select(Finding.type, func.count())
        .join(Scan, Finding.scan_id == Scan.id)
        .where(*scan_time_filter)
        .group_by(Finding.type)
        .order_by(func.count().desc())
    )
    findings_by_type = [
        {"type": row[0], "count": int(row[1])} for row in f_by_type.fetchall()
    ]

    f_by_sev = await session.execute(
        select(Finding.severity, func.count())
        .join(Scan, Finding.scan_id == Scan.id)
        .where(*scan_time_filter)
        .group_by(Finding.severity)
        .order_by(func.count().desc())
    )
    findings_by_severity = [
        {"severity": row[0], "count": int(row[1])} for row in f_by_sev.fetchall()
    ]

    success_rate = (
        round(100.0 * completed / created, 1) if created > 0 else None
    )

    return {
        "period": period,
        "from": since.isoformat() if since else None,
        "to": until.isoformat(),
        "summary": {
            "scans_created": created,
            "scans_completed": completed,
            "scans_failed": failed,
            "scans_queued_in_period": queued_period,
            "scans_running_in_period": running_period,
            "queued_now": queued_now,
            "running_now": running_now,
            "success_rate_pct": success_rate,
            "unique_ips": unique_ips,
            "avg_completion_sec": avg_completion_sec,
            "findings_total": findings_total,
        },
        "by_status": by_status,
        "top_target_urls": top_urls,
        "findings_by_type": findings_by_type,
        "findings_by_severity": findings_by_severity,
    }