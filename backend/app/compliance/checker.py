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
from app.compliance.spa_bundle_scan import SpaBundleScan, analyze_spa_bundles
from app.data.penalties import get_penalty, penalty_color
from app.scan.access_findings import blocked_scan_finding
from app.scan.fetch import fetch_target_page

COOKIE_MARKERS = ("cookie", "consent", "gdpr", "куки", "согласие")
FOREIGN_SDK_MARKERS = (
    "firebase",
    "googleapis.com",
    "fcm.googleapis.com",
    "googletagmanager",
    "google-analytics",
    "facebook",
    "amplitude",
    "mixpanel",
)

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


def _forms_without_consent_checkbox(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    problematic: list[str] = []
    for form in soup.find_all("form"):
        inputs = form.find_all("input")
        has_submit = any(
            t.get("type", "").lower() in ("submit", "button") or t.name == "button"
            for t in inputs
        )
        if not has_submit and not form.find("button"):
            continue
        has_consent = False
        for inp in inputs:
            if inp.get("type", "").lower() != "checkbox":
                continue
            ctx = inp.get_text(" ", strip=True).lower()
            parent = inp.find_parent()
            if parent:
                ctx += " " + parent.get_text(" ", strip=True).lower()
            if any(k in ctx for k in ("соглас", "персональн", "privacy", "consent", "152")):
                has_consent = True
                break
        if not has_consent:
            action = form.get("action") or "(текущая страница)"
            problematic.append(action)
    return problematic


def _sdk_haystack(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            parts.append(str(src))
        elif tag.string:
            parts.append(tag.string[:8000])
    for tag in soup.find_all("iframe", src=True):
        parts.append(str(tag["src"]))
    return " ".join(parts).lower()


def _detect_foreign_sdks(html: str) -> list[str]:
    haystack = _sdk_haystack(html)
    if not haystack.strip():
        return []
    found: list[str] = []
    for marker in FOREIGN_SDK_MARKERS:
        if marker in haystack:
            found.append(marker)
    return found


def run_compliance_checks(
    html: str, *, privacy_found: bool, consent_markers_found: bool
) -> list[RawFinding]:
    findings: list[RawFinding] = []

    if not privacy_found:
        findings.append(
            RawFinding(
                penalty_code="no_privacy_policy",
                title="Не найдена политика конфиденциальности",
                description=(
                    "На проверенной странице и по типовым ссылкам (/privacy, "
                    "политика конфиденциальности и т.п.) документ не обнаружен. "
                    "Если политика есть только во внутренних разделах или открывается "
                    "через JavaScript, укажите прямую ссылку на неё в проверке."
                ),
                severity="medium",
            )
        )

    if not consent_markers_found and not _has_cookie_banner(html):
        findings.append(
            RawFinding(
                penalty_code="no_cookie_banner",
                title="Не обнаружен cookie/consent-баннер",
                description=(
                    "В HTML нет признаков баннера согласия на cookie "
                    "(cookie, consent, gdpr и т.п.)."
                ),
                severity="high",
            )
        )

    forms = _forms_without_consent_checkbox(html)
    if forms:
        findings.append(
            RawFinding(
                penalty_code="processing_without_consent",
                title="Форма без чекбокса согласия",
                description=(
                    f"Обнаружено форм без чекбокса согласия: {len(forms)}. "
                    f"Пример action: {forms[0]}"
                ),
                severity="high",
            )
        )

    sdks = _detect_foreign_sdks(html)
    if sdks:
        findings.append(
            RawFinding(
                penalty_code="foreign_sdk_transfer",
                title="Обнаружены иностранные SDK/скрипты",
                description=f"В подключённых скриптах найдены: {', '.join(sorted(set(sdks)))}.",
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
        "title": entry.title,
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