"""Считает перцентили длительности успешных сканов (на сервере: docker exec backend)."""
from __future__ import annotations

import asyncio
import statistics

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.entities import Scan, ScanStatus


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Scan).where(
                Scan.status == ScanStatus.COMPLETED.value,
                Scan.completed_at.isnot(None),
            )
        )
        scans = list(result.scalars())
    durs: list[float] = []
    for s in scans:
        if not s.completed_at or not s.created_at:
            continue
        durs.append((s.completed_at - s.created_at).total_seconds())
    durs.sort()
    n = len(durs)
    if n == 0:
        print("completed_scans=0")
        return
    p50 = percentile(durs, 0.5)
    p90 = percentile(durs, 0.9)
    p95 = percentile(durs, 0.95)
    print(f"completed_scans={n}")
    print(f"p50_sec={p50:.1f} p50_min={p50/60:.2f}")
    print(f"p90_sec={p90:.1f} p90_min={p90/60:.2f}")
    print(f"p95_sec={p95:.1f} p95_min={p95/60:.2f}")
    print(f"max_sec={durs[-1]:.1f} max_min={durs[-1]/60:.2f}")
    print(f"mean_sec={statistics.mean(durs):.1f}")
    over10 = sum(1 for t in durs if t > 600)
    over7 = sum(1 for t in durs if t > 420)
    print(f"over_7min={over7} ({100*over7/n:.1f}%)")
    print(f"over_10min={over10} ({100*over10/n:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())