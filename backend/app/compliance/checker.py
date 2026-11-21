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
from app.scan.site_scan import fetch_scan_site

COOKIE_MARKERS = ("cookie", "consent", "gdpr", "куки", "согласие")

CHECK_SCOPE_NOTE = (
    "До 15 страниц того же сайта: точка входа, переходы с неё и выборка из sitemap; "
    "плюс robots.txt и типовые адреса политики."
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
    extra_pages: list[tuple[str, str]] | None = None,
) -> tuple[bool, str | None]:
    pages = [(page_url, html), *(extra_pages or [])]

    for url, body in pages:
        if _page_content_is_privacy_policy(body):
            return True, f"Документ на странице: {url}"

    candidates: list[str] = []
    for url, body in pages:
        candidates = _merge_candidates(
            candidates, collect_privacy_candidate_urls(url, body)
        )
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
        if _page_content_is_privacy_policy(fetched.html):
            return True, f"Документ на странице: {candidate}"
        if _raw_html_mentions_privacy_url(candidate, fetched.html):
            if _main_page_has_privacy_signal(fetched.html):
                return True, f"Страница политики: {candidate}"

    if spa.privacy_found:
        label = spa.privacy_script_url or "JavaScript-приложение"
        return True, f"Маршрут или текст в SPA: {label}"

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


def run_compliance_checks_site(
    pages: list[tuple[str, str]],
    *,
    privacy_found: bool,
    consent_markers_found: bool,
) -> list[RawFinding]:
    findings: list[RawFinding] = []
    page_count = len(pages)

    tracking: set[str] = set()
    foreign: set[str] = set()
    form_actions: list[str] = []
    form_seen: set[str] = set()

    for _, html in pages:
        tracking.update(detect_measurable_tracking(html))
        foreign.update(detect_foreign_analytics(html))
        for action in forms_missing_pdn_consent(html):
            if action not in form_seen:
                form_seen.add(action)
                form_actions.append(action)

    tracking_list = sorted(tracking)
    foreign_list = sorted(foreign)

    if not privacy_found:
        findings.append(
            RawFinding(
                penalty_code="no_privacy_policy",
                title="Не опубликована политика обработки ПДн",
                description=(
                    format_finding_preamble("no_privacy_policy")
                    + f"На {page_count} проверенных страницах и типовых адресах "
                    "документ не найден. "
                    "Если политика только во внутреннем разделе — укажите прямую ссылку."
                ),
                severity="medium",
            )
        )

    if tracking_list and not consent_markers_found:
        findings.append(
            RawFinding(
                penalty_code="no_cookie_banner",
                title="Нет согласия при подключённой аналитике",
                description=(
                    format_finding_preamble("no_cookie_banner")
                    + f"На {page_count} страницах найдены скрипты: {', '.join(tracking_list)}. "
                    "Баннер или иной механизм согласия на cookie не обнаружен."
                ),
                severity="high",
            )
        )

    if form_actions:
        findings.append(
            RawFinding(
                penalty_code="processing_without_consent",
                title="Сбор ПДн в форме без согласия",
                description=(
                    format_finding_preamble("processing_without_consent")
                    + f"На {page_count} страницах: форм с ПДн без согласия — "
                    f"{len(form_actions)} (поиск и вход не учитываются). "
                    f"Пример: {form_actions[0]}."
                ),
                severity="high",
            )
        )

    if foreign_list:
        findings.append(
            RawFinding(
                penalty_code="foreign_sdk_transfer",
                title="Иностранная аналитика/реклама (трансграничная передача)",
                description=(
                    format_finding_preamble("foreign_sdk_transfer")
                    + f"На проверенных страницах подключены: {', '.join(foreign_list)}."
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
    privacy_found: bool | None,
    privacy_source: str | None,
    consent_found: bool | None,
    consent_source: str | None,
    requested_url: str | None = None,
    scanned_url: str | None = None,
    used_fallback: bool = False,
    tried_urls: list[str] | None = None,
    scanned_urls: list[str] | None = None,
    pages_checked: int | None = None,
) -> dict[str, Any]:
    scope = CHECK_SCOPE_NOTE
    if used_fallback and scanned_url and requested_url:
        scope = (
            f"Запрошен {requested_url}. Точка входа — {scanned_url} "
            f"(главная закрыта антиботом, переход на /contacts/ и аналоги). "
            f"Далее до 15 внутренних страниц с точки входа и из sitemap."
        )
    ctx: dict[str, Any] = {
        "scope": scope,
        "privacy_found": privacy_found,
        "privacy_source": privacy_source,
        "consent_found": consent_found,
        "consent_source": consent_source,
    }
    if requested_url:
        ctx["requested_url"] = requested_url
    if scanned_url:
        ctx["scanned_url"] = scanned_url
    if used_fallback:
        ctx["used_fallback"] = True
    if tried_urls:
        ctx["tried_urls"] = tried_urls
    if scanned_urls:
        ctx["scanned_urls"] = scanned_urls
    if pages_checked is not None:
        ctx["pages_checked"] = pages_checked
    return ctx


async def check_url_compliance(url: str) -> tuple[list[dict], dict[str, Any]]:
    normalized = validate_target_url(url)
    bundle = await fetch_scan_site(normalized)
    entry = bundle.entry
    fetch = entry.result
    page_url = entry.fetched_url
    page_pairs = bundle.page_pairs

    def _empty_ctx() -> dict[str, Any]:
        ctx = compliance_context_dict(
            privacy_found=None,
            privacy_source=None,
            consent_found=None,
            consent_source=None,
            requested_url=normalized,
            scanned_url=page_url,
            used_fallback=entry.used_fallback,
            tried_urls=entry.tried_urls,
            scanned_urls=[],
            pages_checked=0,
        )
        ctx["scope"] = (
            CHECK_SCOPE_NOTE
            + " Содержимое страниц не прочитано — поиск политики и форм не выполнялся."
        )
        return ctx

    if not bundle.html_available:
        return [
            blocked_scan_finding(
                "compliance", fetch, tried_urls=entry.tried_urls
            )
        ], _empty_ctx()

    html = entry.html or ""
    extra_pages = [(u, h) for u, h in page_pairs if u.rstrip("/") != page_url.rstrip("/")]
    spa = await analyze_spa_bundles(page_url, html)
    privacy_found, privacy_source = await _locate_privacy_policy(
        page_url, html, spa=spa, extra_pages=extra_pages
    )

    consent_found = spa.consent_found or any(
        _has_cookie_banner(h) for _, h in page_pairs
    )
    consent_source: str | None = None
    if spa.consent_found:
        consent_source = (
            f"Код приложения (SPA): {spa.consent_script_url}"
            if spa.consent_script_url
            else "Код приложения (SPA)"
        )
    else:
        for url, body in page_pairs:
            if _has_cookie_banner(body):
                consent_source = f"Признаки согласия на странице: {url}"
                break

    findings = [
        enrich_finding(f)
        for f in run_compliance_checks_site(
            page_pairs,
            privacy_found=privacy_found,
            consent_markers_found=consent_found,
        )
    ]
    scanned_urls = [p.url for p in bundle.pages]
    ctx = compliance_context_dict(
        privacy_found=privacy_found,
        privacy_source=privacy_source,
        consent_found=consent_found,
        consent_source=consent_source,
        requested_url=normalized,
        scanned_url=page_url,
        used_fallback=entry.used_fallback,
        tried_urls=entry.tried_urls,
        scanned_urls=scanned_urls,
        pages_checked=len(scanned_urls),
    )
    return findings, ctx