from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from urllib.parse import urljoin

from app.compliance.privacy_detection import (
    MAX_EXTRA_FETCHES,
    _main_page_has_privacy_signal,
    _page_content_is_privacy_policy,
    _raw_html_mentions_privacy_url,
    collect_privacy_candidate_urls,
    privacy_urls_from_robots,
)
from app.compliance.spa_bundle_scan import spa_bundle_has_consent, spa_bundle_has_privacy
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


async def _locate_privacy_policy(page_url: str, html: str) -> tuple[bool, str | None]:
    if _main_page_has_privacy_signal(html) or _raw_html_mentions_privacy_url(
        page_url, html
    ):
        return True, page_url

    candidates = collect_privacy_candidate_urls(page_url, html)
    robots = await fetch_target_page(urljoin(page_url, "/robots.txt"))
    if robots.html and len(robots.html) < 500_000:
        candidates = _merge_candidates(
            candidates, privacy_urls_from_robots(page_url, robots.html)
        )

    for candidate in candidates[:MAX_EXTRA_FETCHES]:
        fetched = await fetch_target_page(candidate)
        if not fetched.html:
            continue
        if _raw_html_mentions_privacy_url(candidate, fetched.html):
            return True, candidate
        if not fetched.html_available:
            continue
        if _page_content_is_privacy_policy(fetched.html):
            return True, candidate
        if _main_page_has_privacy_signal(fetched.html):
            return True, candidate

    if await spa_bundle_has_privacy(page_url, html):
        return True, urljoin(page_url, "/privacy")

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


def _detect_foreign_sdks(html: str) -> list[str]:
    lower = html.lower()
    found: list[str] = []
    for marker in FOREIGN_SDK_MARKERS:
        if marker in lower:
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
                description=f"В коде страницы найдены: {', '.join(sorted(set(sdks)))}.",
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


async def check_url_compliance(url: str) -> list[dict]:
    normalized = validate_target_url(url)
    fetch = await fetch_target_page(normalized)
    findings: list[dict] = []

    if not fetch.html_available:
        findings.append(blocked_scan_finding("compliance", fetch))
        return findings

    html = fetch.html or ""
    privacy_found, _privacy_source = await _locate_privacy_policy(normalized, html)
    consent_in_spa = await spa_bundle_has_consent(normalized, html)
    findings.extend(
        enrich_finding(f)
        for f in run_compliance_checks(
            html,
            privacy_found=privacy_found,
            consent_markers_found=consent_in_spa,
        )
    )
    return findings