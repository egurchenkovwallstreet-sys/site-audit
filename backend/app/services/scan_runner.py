from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.checker import check_url_compliance
from app.models.entities import Finding, Scan, ScanStatus
from app.scan.site_scan import fetch_scan_site
from app.scan.technical_checker import check_url_technical


async def run_compliance_scan(session: AsyncSession, scan: Scan) -> Scan:
    scan.status = ScanStatus.RUNNING.value
    await session.commit()

    try:
        rows: list[dict] = []
        context: dict | None = None
        bundle = await fetch_scan_site(scan.target_url)
        try:
            compliance_rows, context = await check_url_compliance(
                scan.target_url,
                bundle=bundle,
            )
            rows.extend(compliance_rows)
        except Exception:
            pass
        try:
            rows.extend(await check_url_technical(scan.target_url, bundle=bundle))
        except Exception:
            pass
        if context is not None:
            scan.context_json = json.dumps(context, ensure_ascii=False)
        for row in rows:
            session.add(
                Finding(
                    scan_id=scan.id,
                    type=row["type"],
                    severity=row["severity"],
                    title=row["title"],
                    description=row["description"],
                    legal_article=row.get("legal_article"),
                    max_penalty=row.get("max_penalty"),
                    color=row.get("color"),
                    min_level=row.get("min_level", 1),
                    remediation=row.get("remediation"),
                )
            )
        scan.status = ScanStatus.COMPLETED.value
        scan.completed_at = datetime.now(timezone.utc)
    except Exception:
        scan.status = ScanStatus.FAILED.value
        scan.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise

    await session.commit()
    await session.refresh(scan)
    return scan