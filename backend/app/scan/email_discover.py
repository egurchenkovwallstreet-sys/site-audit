from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from app.compliance.form_consent import script_url_is_vendor_bundle
from app.compliance.spa_bundle_scan import SpaBundleScan, _discover_script_urls
from app.scan.fetch import MAX_SCRIPT_BYTES, fetch_resource_text, fetch_target_page
from app.scan.page_fetch import page_is_readable

EMAIL_IN_TEXT = re.compile(
    r"(?<![\w.@])([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})(?![\w.@])"
)

JUNK_LOCAL_PARTS = frozenset(
    {
        "noreply",
        "no-reply",
        "donotreply",
        "mailer-daemon",
        "postmaster",
        "example",
        "test",
        "user",
        "email",
        "your",
        "name",
    }
)

JUNK_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "domain.com",
        "email.com",
        "yoursite.com",
        "wixpress.com",
        "sentry.io",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "schema.org",
        "w3.org",
    }
)

MAX_EMAILS = 12
MAX_LEGAL_FETCHES = 5

LEGAL_PAGE_HINTS = (
    "contact",
    "kontakt",
    "контакт",
    "about",
    "feedback",
    "offer",
    "oferta",
    "оферт",
    "public-offer",
    "politik",
    "privacy",
    "konfid",
    "legal",
    "policy",
    "договор",
    "персональн",
)


def _normalize_email(raw: str) -> str | None:
    addr = unquote(raw).strip().lower().rstrip(".")
    if not addr or "@" not in addr:
        return None
    local, _, domain = addr.partition("@")
    if not local or not domain or "." not in domain:
        return None
    if any(c in addr for c in ("..", "@.", ".@", " ")):
        return None
    if local in JUNK_LOCAL_PARTS:
        return None
    if domain in JUNK_DOMAINS:
        return None
    if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        return None
    return addr


def _emails_from_raw_text(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in EMAIL_IN_TEXT.finditer(text):
        norm = _normalize_email(match.group(1))
        if norm and norm not in seen:
            seen.add(norm)
            found.append(norm)
    return found


def _emails_from_html(html: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")

    def add(raw: str) -> None:
        norm = _normalize_email(raw)
        if norm and norm not in seen:
            seen.add(norm)
            found.append(norm)

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if href.lower().startswith("mailto:"):
            body = href[7:].split("?", 1)[0]
            add(body)

    for script in soup.find_all("script"):
        script.decompose()
    for style in soup.find_all("style"):
        style.decompose()

    text = soup.get_text(" ", strip=True)
    for email in _emails_from_raw_text(text):
        add(email)

    return found


def _site_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def discover_contact_emails(
    pages: list[tuple[str, str]],
    *,
    site_url: str | None = None,
) -> list[str]:
    """Адреса с просмотренных HTML-страниц (контакты, главная и т.д.)."""
    site_host = _site_domain(site_url) if site_url else ""
    ranked: dict[str, int] = {}

    for page_url, html in pages:
        if not html or len(html) < 20:
            continue
        extract = (
            _emails_from_raw_text(html)
            if page_url.startswith("spa-bundle:")
            else _emails_from_html(html)
        )
        for email in extract:
            score = ranked.get(email, 0)
            mail_host = email.split("@")[-1]
            if site_host and mail_host.removeprefix("www.") == site_host:
                score += 3
            low_url = page_url.lower()
            if any(hint in low_url for hint in LEGAL_PAGE_HINTS):
                score += 2
            if "spa-bundle:" in low_url or "main.dart" in low_url:
                score += 2
            ranked[email] = max(ranked.get(email, 0), score)

    ordered = sorted(ranked.keys(), key=lambda e: (-ranked[e], e))
    return ordered[:MAX_EMAILS]


def _legal_url_priority(url: str) -> int:
    low = url.lower()
    if any(x in low for x in ("offer", "oferta", "оферт", "public-offer", "dogovor")):
        return 0
    if any(x in low for x in ("politik", "privacy", "konfid", "legal-documents", "pdn")):
        return 1
    return 2


async def gather_pages_for_email_search(
    site_url: str,
    entry_url: str,
    entry_html: str,
    scanned_pages: list[tuple[str, str]],
    *,
    spa: SpaBundleScan | None = None,
    max_legal_fetches: int = MAX_LEGAL_FETCHES,
) -> list[tuple[str, str]]:
    """Доп. загрузка политики/оферты — там чаще всего указан e-mail оператора."""
    seen = {u.rstrip("/") for u, _ in scanned_pages if u}
    merged = list(scanned_pages)

    if spa and spa.privacy_found and spa.privacy_script_url:
        return merged

    from app.compliance.privacy_detection import collect_privacy_candidate_urls

    candidates = collect_privacy_candidate_urls(entry_url, entry_html or "")
    candidates.sort(key=_legal_url_priority)

    for url in candidates:
        if len(merged) - len(scanned_pages) >= max_legal_fetches:
            break
        key = url.rstrip("/")
        if key in seen:
            continue
        res = await fetch_target_page(url)
        if not page_is_readable(res.html, res.status_code):
            continue
        merged.append((url, res.html or ""))
        seen.add(key)

    return merged


async def _spa_bundle_pages_for_email(
    page_url: str,
    entry_html: str,
    spa: SpaBundleScan | None,
    *,
    max_bundles: int = 4,
) -> list[tuple[str, str]]:
    """Flutter/SPA: оферта и политика часто только в main.dart.js и др. бандлах."""
    script_urls: list[str] = []
    cached: dict[str, str] = {}
    if spa and spa.privacy_script_url:
        script_urls.append(spa.privacy_script_url)
        if spa.privacy_script_body:
            cached[spa.privacy_script_url] = spa.privacy_script_body
    if spa and spa.consent_script_url:
        if spa.consent_script_url not in script_urls:
            script_urls.append(spa.consent_script_url)
        if spa.consent_script_body:
            cached[spa.consent_script_url] = spa.consent_script_body
    for candidate in _discover_script_urls(page_url, entry_html or ""):
        if candidate in script_urls:
            continue
        if script_url_is_vendor_bundle(candidate):
            continue
        script_urls.append(candidate)

    pages: list[tuple[str, str]] = []
    for script_url in script_urls[:max_bundles]:
        body = cached.get(script_url)
        if body is None:
            body = await fetch_resource_text(script_url, max_bytes=MAX_SCRIPT_BYTES)
        if not body or len(body) < 80:
            continue
        low = body.lower()
        if not any(
            marker in low
            for marker in (
                "@",
                "mailto",
                "offer",
                "public_offer",
                "оферт",
                "privacy",
                "politik",
                "конфид",
            )
        ):
            continue
        pages.append((f"spa-bundle:{script_url}", body))
    return pages


async def discover_contact_emails_for_site(
    site_url: str,
    entry_url: str,
    entry_html: str,
    scanned_pages: list[tuple[str, str]],
    *,
    spa: SpaBundleScan | None = None,
) -> list[str]:
    pages = await gather_pages_for_email_search(
        site_url,
        entry_url,
        entry_html,
        scanned_pages,
        spa=spa,
    )
    pages.extend(await _spa_bundle_pages_for_email(entry_url, entry_html, spa))
    return discover_contact_emails(pages, site_url=site_url)