from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import Scan


class ScanRateLimitExceeded(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


async def assert_scan_rate_allowed(session: AsyncSession, client_ip: str) -> None:
    if not client_ip or client_ip == "unknown":
        return

    settings = get_settings()
    if client_ip in settings.scan_rate_limit_bypass_ip_set():
        return
    now = datetime.now(timezone.utc)

    async def count_since(delta: timedelta) -> int:
        since = now - delta
        q = await session.execute(
            select(func.count())
            .select_from(Scan)
            .where(
                Scan.client_ip == client_ip,
                Scan.created_at >= since,
            )
        )
        return int(q.scalar_one())

    burst = await count_since(timedelta(minutes=10))
    if burst >= settings.scan_rate_limit_burst_10min:
        raise ScanRateLimitExceeded(
            "Слишком частые запросы на проверку. Подождите несколько минут."
        )

    per_hour = await count_since(timedelta(hours=1))
    if per_hour >= settings.scan_rate_limit_per_hour:
        raise ScanRateLimitExceeded(
            "Превышен лимит проверок за последний час. Попробуйте позже."
        )

    per_day = await count_since(timedelta(hours=24))
    if per_day >= settings.scan_rate_limit_per_day:
        raise ScanRateLimitExceeded(
            "Превышен дневной лимит проверок. Попробуйте завтра."
        )