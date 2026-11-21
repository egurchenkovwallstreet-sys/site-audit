from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.compliance.privacy_detection import (
    MAX_EXTRA_FETCHES,
    _main_page_has_privacy_signal,
    _page_content_is_privacy_policy,
    _raw_html_mentions_privacy_url,
    collect_privacy_candidate_urls,
    privacy_urls_from_robots,
    privacy_urls_from_sitemap,
)
from app.compliance.form_consent import forms_missing_pdn_consent
from app.compliance.legal_basis import format_finding_preamble
from app.compliance.spa_bundle_scan import SpaBundleScan, analyze_spa_bundles
from app.compliance.tracking_scripts import (
    detect_foreign_analytics,
    detect_measurable_tracking,
)
from app.data.penalties import get_penalty, penalty_color
from app.scan.access_findings import blocked_scan_finding
from app.scan.fetch import fetch_target_page

COOKIE_MARKERS = ("cookie", "consent", "gdpr", "куки", "согласие")

CHECK_SCOPE_NOTE = (
    "Проверены главная страница, типовые ссылки на политику, robots.txt и sitemap.xml."
)


@dataclass(slots=True)
class RawFinding:
    penalty_code: str
    title: str
    description: str
    severity: str


def validate_target_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Разрешены только URL с http или https")
    if not parsed.netloc:
        raise ValueError("Некорректный URL")
    return url.strip()


def _merge_candidates(primary: list[str], extra: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for url in [*primary, *extra]:
        key = url.rstrip("/")
        if key not in seen:
            seen.add(key)
            merged.append(url)
    return merged


async def _locate_privacy_policy(
    page_url: str,
    html: str,
    *,
    spa: SpaBundleScan,
) -> tuple[bool, str | None]:
    if _main_page_has_privacy_signal(html):
        return True, "Ссылка или текст на главной странице"
    if _raw_html_mentions_privacy_url(page_url, html):
        return True, "Упоминание политики в коде главной страницы"

    candidates = collect_privacy_candidate_urls(page_url, html)
    robots = await fetch_target_page(urljoin(page_url, "/robots.txt"))
    if robots.html and len(robots.html) < 500_000:
        candidates = _merge_candidates(
            candidates, privacy_urls_from_robots(page_url, robots.html)
        )

    sitemap = await fetch_target_page(urljoin(page_url, "/sitemap.xml"))
    if sitemap.html and len(sitemap.html) < 2_000_000:
        candidates = _merge_candidates(
            candidates, privacy_urls_from_sitemap(page_url, sitemap.html)
        )

    for candidate in candidates[:MAX_EXTRA_FETCHES]:
        fetched = await fetch_target_page(candidate)
        if not fetched.html:
            continue
        if _raw_html_mentions_privacy_url(candidate, fetched.html):
            return True, f"Отдельная страница: {candidate}"
        if not fetched.html_available:
            continue
        if _page_content_is_privacy_policy(fetched.html):
            return True, f"Документ на странице: {candidate}"
        if _main_page_has_privacy_signal(fetched.html):
            return True, f"Ссылка на странице: {candidate}"

    if spa.privacy_found:
        label = spa.privacy_script_url or "JavaScript-приложение"
        return True, f"Код приложения (SPA): {label}"

    return False, None


def _has_cookie_banner(html: str) -> bool:
    lower = html.lower()
    if any(m in lower for m in COOKIE_MARKERS):
        return True
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        attrs = " ".join(
            str(tag.get(attr, "")) for attr in ("id", "class", "aria-label", "data-testid")
        ).lower()
        if any(m in attrs for m in COOKIE_MARKERS):
            return True
    return False


def run_compliance_checks(
    html: str, *, privacy_found: bool, consent_markers_found: bool
) -> list[RawFinding]:
    findings: list[RawFinding] = []

    tracking = detect_measurable_tracking(html)

    if not privacy_found:
        findings.append(
            RawFinding(
                penalty_code="no_privacy_policy",
                title="Не опубликована политика обработки ПДн",
                description=(
                    format_finding_preamble("no_privacy_policy")
                    + "Документ не найден на главной и по типовым адресам "
                    "(/privacy, политика в футере, robots/sitemap, SPA). "
                    "Если политика только во внутреннем разделе — проверьте по прямой ссылке."
                ),
                severity="medium",
            )
        )

    if tracking and not consent_markers_found and not _has_cookie_banner(html):
        findings.append(
            RawFinding(
                penalty_code="no_cookie_banner",
                title="Нет согласия при подключённой аналитике",
                description=(
                    format_finding_preamble("no_cookie_banner")
                    + f"Обнаружены скрипты аналитики/рекламы: {', '.join(tracking)}. "
                    "Баннер или иной механизм согласия на cookie не найден."
                ),
                severity="high",
            )
        )

    forms = forms_missing_pdn_consent(html)
    if forms:
        findings.append(
            RawFinding(
                penalty_code="processing_without_consent",
                title="Сбор ПДн в форме без согласия",
                description=(
                    format_finding_preamble("processing_without_consent")
                    + f"Форм с полями ПДн без согласия: {len(forms)} "
                    f"(поиск и вход не учитываются). Пример: {forms[0]}."
                ),
                severity="high",
            )
        )

    foreign = detect_foreign_analytics(html)
    if foreign:
        findings.append(
            RawFinding(
                penalty_code="foreign_sdk_transfer",
                title="Иностранная аналитика/реклама (трансграничная передача)",
                description=(
                    format_finding_preamble("foreign_sdk_transfer")
                    + f"Подключены скрипты: {', '.join(foreign)}."
                ),
                severity="high",
            )
        )

    return findings


def enrich_finding(raw: RawFinding) -> dict:
    entry = get_penalty(raw.penalty_code)
    if entry is None:
        return {
            "type": "compliance",
            "severity": raw.severity,
            "title": raw.title,
            "description": raw.description,
            "legal_article": None,
            "max_penalty": None,
            "color": "green",
            "min_level": 1,
            "remediation": None,
        }
    return {
        "type": "compliance",
        "severity": entry.severity,
        "title": raw.title,
        "description": raw.description,
        "legal_article": entry.legal_article,
        "max_penalty": entry.max_penalty,
        "color": penalty_color(entry.max_penalty),
        "min_level": 1,
        "remediation": entry.remediation,
    }


def compliance_context_dict(
    *,
    privacy_found: bool,
    privacy_source: str | None,
    consent_found: bool,
    consent_source: str | None,
) -> dict[str, Any]:
    return {
        "scope": CHECK_SCOPE_NOTE,
        "privacy_found": privacy_found,
        "privacy_source": privacy_source,
        "consent_found": consent_found,
        "consent_source": consent_source,
    }


async def check_url_compliance(url: str) -> tuple[list[dict], dict[str, Any]]:
    normalized = validate_target_url(url)
    fetch = await fetch_target_page(normalized)
    empty_ctx = compliance_context_dict(
        privacy_found=False,
        privacy_source=None,
        consent_found=False,
        consent_source=None,
    )

    if not fetch.html_available:
        return [blocked_scan_finding("compliance", fetch)], empty_ctx

    html = fetch.html or ""
    spa = await analyze_spa_bundles(normalized, html)
    privacy_found, privacy_source = await _locate_privacy_policy(
        normalized, html, spa=spa
    )

    consent_in_html = _has_cookie_banner(html)
    consent_found = spa.consent_found or consent_in_html
    consent_source: str | None = None
    if spa.consent_found:
        consent_source = (
            f"Код приложения (SPA): {spa.consent_script_url}"
            if spa.consent_script_url
            else "Код приложения (SPA)"
        )
    elif consent_in_html:
        consent_source = "Признаки согласия в HTML главной страницы"

    findings = [
        enrich_finding(f)
        for f in run_compliance_checks(
            html,
            privacy_found=privacy_found,
            consent_markers_found=consent_found,
        )
    ]
    ctx = compliance_context_dict(
        privacy_found=privacy_found,
        privacy_source=privacy_source,
        consent_found=consent_found,
        consent_source=consent_source,
    )
    return findings, ctx