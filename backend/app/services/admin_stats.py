from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Finding, Payment, PaymentStatus, Scan, ScanStatus

PeriodKey = Literal["day", "week", "month", "all"]

# tier в payments совпадает с variant отчёта (short / extended)
REPORT_PRODUCTS: tuple[tuple[str, str, int], ...] = (
    ("short", "Краткий отчёт", 490),
    ("extended", "Расширенный отчёт", 990),
)


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

    prior_ips_subq: select | None = None
    if since is not None:
        prior_ips_subq = (
            select(Scan.client_ip)
            .where(Scan.client_ip.isnot(None), Scan.created_at < since)
            .distinct()
            .scalar_subquery()
        )

    if prior_ips_subq is not None:
        new_ips_q = await session.execute(
            select(func.count(func.distinct(Scan.client_ip))).where(
                *scan_filter,
                Scan.client_ip.isnot(None),
                Scan.client_ip.not_in(prior_ips_subq),
            )
        )
        scans_new_ip_q = await session.execute(
            select(func.count())
            .select_from(Scan)
            .where(
                *scan_filter,
                Scan.client_ip.isnot(None),
                Scan.client_ip.not_in(prior_ips_subq),
            )
        )
        new_unique_ips = int(new_ips_q.scalar_one())
        scans_from_new_ips = int(scans_new_ip_q.scalar_one())

        top_new_ips_rows = await session.execute(
            select(Scan.client_ip, func.count())
            .where(
                *scan_filter,
                Scan.client_ip.isnot(None),
                Scan.client_ip.not_in(prior_ips_subq),
            )
            .group_by(Scan.client_ip)
            .order_by(func.count().desc())
            .limit(15)
        )
        new_ips_breakdown = [
            {"client_ip": row[0], "scans_in_period": int(row[1])}
            for row in top_new_ips_rows.fetchall()
        ]
    else:
        new_unique_ips = unique_ips
        scans_new_ip_q = await session.execute(
            select(func.count())
            .select_from(Scan)
            .where(*scan_filter, Scan.client_ip.isnot(None))
        )
        scans_from_new_ips = int(scans_new_ip_q.scalar_one())
        top_all_ips = await session.execute(
            select(Scan.client_ip, func.count())
            .where(Scan.client_ip.isnot(None))
            .group_by(Scan.client_ip)
            .order_by(func.count().desc())
            .limit(15)
        )
        new_ips_breakdown = [
            {"client_ip": row[0], "scans_in_period": int(row[1])}
            for row in top_all_ips.fetchall()
        ]

    payment_time_filter = [Payment.created_at >= since] if since is not None else []

    async def payment_agg(*extra) -> tuple[int, int]:
        q = await session.execute(
            select(func.count(), func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .where(
                *payment_time_filter,
                *extra,
            )
        )
        row = q.one()
        return int(row[0]), int(row[1])

    pay_ok_n, pay_ok_sum = await payment_agg(
        Payment.status == PaymentStatus.SUCCEEDED.value
    )
    pay_pending_n, pay_pending_sum = await payment_agg(
        Payment.status == PaymentStatus.PENDING.value
    )
    pay_all_n, pay_all_sum = await payment_agg()

    pay_by_tier = await session.execute(
        select(Payment.tier, func.count(), func.coalesce(func.sum(Payment.amount), 0))
        .where(
            *payment_time_filter,
            Payment.status == PaymentStatus.SUCCEEDED.value,
        )
        .group_by(Payment.tier)
        .order_by(Payment.tier)
    )
    payments_by_tier = [
        {"tier": row[0], "count": int(row[1]), "amount_rub": int(row[2])}
        for row in pay_by_tier.fetchall()
    ]
    tier_index = {row["tier"]: row for row in payments_by_tier}
    payments_by_report: list[dict[str, Any]] = []
    for tier, label, list_price_rub in REPORT_PRODUCTS:
        row = tier_index.get(tier, {"count": 0, "amount_rub": 0})
        payments_by_report.append(
            {
                "tier": tier,
                "label": label,
                "list_price_rub": list_price_rub,
                "count": int(row.get("count", 0)),
                "amount_rub": int(row.get("amount_rub", 0)),
            }
        )
    short_row = next((r for r in payments_by_report if r["tier"] == "short"), None)
    ext_row = next((r for r in payments_by_report if r["tier"] == "extended"), None)

    pay_by_status = await session.execute(
        select(Payment.status, func.count(), func.coalesce(func.sum(Payment.amount), 0))
        .where(*payment_time_filter)
        .group_by(Payment.status)
        .order_by(Payment.status)
    )
    payments_by_status = [
        {"status": row[0], "count": int(row[1]), "amount_rub": int(row[2])}
        for row in pay_by_status.fetchall()
    ]

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
            "new_unique_ips": new_unique_ips,
            "scans_from_new_ips": scans_from_new_ips,
            "avg_completion_sec": avg_completion_sec,
            "findings_total": findings_total,
            "payments_succeeded_count": pay_ok_n,
            "payments_succeeded_sum_rub": pay_ok_sum,
            "payments_pending_count": pay_pending_n,
            "payments_pending_sum_rub": pay_pending_sum,
            "payments_all_count": pay_all_n,
            "payments_all_sum_rub": pay_all_sum,
            "payments_short_count": short_row["count"] if short_row else 0,
            "payments_short_sum_rub": short_row["amount_rub"] if short_row else 0,
            "payments_extended_count": ext_row["count"] if ext_row else 0,
            "payments_extended_sum_rub": ext_row["amount_rub"] if ext_row else 0,
        },
        "by_status": by_status,
        "new_ips": new_ips_breakdown,
        "payments_by_report": payments_by_report,
        "payments_by_tier": payments_by_tier,
        "payments_by_status": payments_by_status,
        "top_target_urls": top_urls,
        "findings_by_type": findings_by_type,
        "findings_by_severity": findings_by_severity,
    }