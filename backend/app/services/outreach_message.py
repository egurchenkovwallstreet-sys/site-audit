from __future__ import annotations

from app.compliance.penalty_totals import sum_breach_penalties, sum_compliance_penalties
from app.config import get_settings
from app.models.entities import Finding, Scan
from app.outreach.email_preview import build_outreach_email_text
from app.services.smtp_send import smtp_is_configured


def outreach_landing_url() -> str:
    landing = get_settings().public_site_url.rstrip("/")
    if "?" in landing:
        return landing + "&utm_source=outreach&utm_medium=email"
    return landing + "/?utm_source=outreach&utm_medium=email"


def compose_outreach_letter(scan: Scan, findings: list[Finding]) -> tuple[str, str]:
    compliance_total = sum_compliance_penalties(findings)
    breach_total = sum_breach_penalties(findings)
    return build_outreach_email_text(
        target_url=scan.target_url,
        compliance_total=compliance_total,
        breach_total=breach_total,
        landing_url=outreach_landing_url(),
    )


def outreach_delivery_meta() -> dict[str, str | bool | None]:
    settings = get_settings()
    return {
        "can_send": smtp_is_configured(),
        "test_inbox_url": settings.mailpit_public_url or None,
        "test_mode": settings.smtp_allow_unauthenticated and not settings.smtp_password,
    }