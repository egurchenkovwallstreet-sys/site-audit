from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AdminIncident, Scan, ScanStatus


def incident_to_dict(row: AdminIncident) -> dict[str, Any]:
    detail: dict[str, Any] | str | None = None
    if row.detail_json:
        try:
            detail = json.loads(row.detail_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            detail = row.detail_json
    return {
        "id": row.id,
        "scan_id": row.scan_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "kind": row.kind,
        "severity": row.severity,
        "title": row.title,
        "target_url": row.target_url,
        "detail": detail,
        "resolved": row.resolved,
    }


async def list_admin_incidents(
    session: AsyncSession,
    *,
    limit: int = 40,
    unresolved_only: bool = True,
) -> list[dict[str, Any]]:
    q = select(AdminIncident).order_by(AdminIncident.created_at.desc()).limit(limit)
    if unresolved_only:
        q = q.where(AdminIncident.resolved.is_(False))
    result = await session.execute(q)
    rows = list(result.scalars())
    return [incident_to_dict(r) for r in rows]


async def backfill_failed_scans(
    session: AsyncSession,
    *,
    limit: int = 30,
) -> int:
    """Исторические failed до журнала — один раз вручную из админки."""
    linked = select(AdminIncident.scan_id).where(AdminIncident.scan_id.isnot(None))
    result = await session.execute(
        select(Scan)
        .where(
            Scan.status == ScanStatus.FAILED.value,
            Scan.id.not_in(linked.scalar_subquery()),
        )
        .order_by(Scan.created_at.desc())
        .limit(limit)
    )
    scans = list(result.scalars())
    created = 0
    for scan in scans:
        detail: dict[str, Any] = {}
        if scan.context_json:
            try:
                raw = json.loads(scan.context_json)
                if isinstance(raw, dict):
                    detail = {
                        "legacy": True,
                        "scan_failed_reason": raw.get("scan_failed_reason"),
                        "pages_checked": raw.get("pages_checked"),
                    }
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        session.add(
            AdminIncident(
                scan_id=scan.id,
                kind="legacy_failed",
                severity="warn",
                title="Старый failed (до журнала сбоев)",
                target_url=scan.target_url,
                detail_json=json.dumps(detail, ensure_ascii=False),
                resolved=False,
            )
        )
        created += 1
    if created:
        await session.commit()
    return created


async def resolve_admin_incident(
    session: AsyncSession,
    incident_id: int,
) -> dict[str, Any] | None:
    row = await session.get(AdminIncident, incident_id)
    if row is None:
        return None
    row.resolved = True
    await session.commit()
    await session.refresh(row)
    return incident_to_dict(row)