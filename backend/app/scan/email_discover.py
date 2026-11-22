from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from app.scan.fetch import fetch_target_page
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
    for match in EMAIL_IN_TEXT.finditer(text):
        add(match.group(1))

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
        for email in _emails_from_html(html):
            score = ranked.get(email, 0)
            mail_host = email.split("@")[-1]
            if site_host and mail_host.removeprefix("www.") == site_host:
                score += 3
            if any(hint in page_url.lower() for hint in LEGAL_PAGE_HINTS):
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
    max_legal_fetches: int = MAX_LEGAL_FETCHES,
) -> list[tuple[str, str]]:
    """Доп. загрузка политики/оферты — там чаще всего указан e-mail оператора."""
    seen = {u.rstrip("/") for u, _ in scanned_pages if u}
    merged = list(scanned_pages)

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


async def discover_contact_emails_for_site(
    site_url: str,
    entry_url: str,
    entry_html: str,
    scanned_pages: list[tuple[str, str]],
) -> list[str]:
    pages = await gather_pages_for_email_search(
        site_url,
        entry_url,
        entry_html,
        scanned_pages,
    )
    return discover_contact_emails(pages, site_url=site_url)