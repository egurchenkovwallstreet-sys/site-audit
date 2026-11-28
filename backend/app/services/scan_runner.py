from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.checker import check_url_compliance
from app.compliance.fz168_checker import check_fz168_pages
from app.models.entities import Finding, Scan, ScanStatus
from app.config import get_settings
from app.scan.nuclei_scan import run_nuclei_scan
from app.scan.scan_budget import ScanTimeBudget
from app.scan.site_scan import fetch_scan_site
from app.scan.seo_checker import check_url_seo
from app.scan.technical_checker import check_url_technical


async def run_compliance_scan(
    session: AsyncSession,
    scan: Scan,
    *,
    time_budget_sec: float | None = None,
) -> Scan:
    from app.services.scan_run_meta import (
        effective_time_budget_sec,
        init_run_meta_on_start,
        read_run_meta,
    )

    scan.status = ScanStatus.RUNNING.value
    init_run_meta_on_start(scan)
    meta = read_run_meta(scan)
    if meta["phase"] >= 2:
        await session.execute(delete(Finding).where(Finding.scan_id == scan.id))
    await session.commit()

    try:
        rows: list[dict] = []
        context: dict | None = None
        limit = time_budget_sec if time_budget_sec is not None else effective_time_budget_sec(scan)
        time_budget = ScanTimeBudget(limit)
        bundle = await fetch_scan_site(scan.target_url, time_budget=time_budget)
        try:
            compliance_rows, context = await check_url_compliance(
                scan.target_url,
                bundle=bundle,
            )
            rows.extend(compliance_rows)
            if bundle.html_available:
                rows.extend(
                    check_fz168_pages(bundle.page_pairs)
                )
        except Exception:
            pass
        try:
            rows.extend(await check_url_seo(scan.target_url, bundle=bundle))
        except Exception:
            pass
        try:
            rows.extend(await check_url_technical(scan.target_url, bundle=bundle))
        except Exception:
            pass
        try:
            if not time_budget.expired():
                rows.extend(
                    await run_nuclei_scan(
                        scan.target_url,
                        timeout_sec=time_budget.remaining(),
                    )
                )
        except Exception:
            pass
        if context is not None:
            settings = get_settings()
            context["time_budget_sec"] = int(limit)
            context["scan_max_pages"] = settings.scan_max_pages
            context["nuclei_enabled"] = settings.nuclei_enabled
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
                    penalty_code=row.get("penalty_code") or row.get("issue_key"),
                )
            )
        scan.status = ScanStatus.COMPLETED.value
        scan.completed_at = datetime.now(timezone.utc)
    except Exception:
        await session.rollback()
        scan = await session.get(Scan, scan.id)
        if scan is not None and scan.status != ScanStatus.COMPLETED.value:
            scan.status = ScanStatus.RUNNING.value
            await session.commit()
        raise

    await session.commit()
    await session.refresh(scan)
    return scan