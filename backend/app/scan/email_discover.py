from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

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
            if any(
                hint in page_url.lower()
                for hint in ("contact", "kontakt", "контакт", "about", "feedback")
            ):
                score += 2
            ranked[email] = max(ranked.get(email, 0), score)

    ordered = sorted(ranked.keys(), key=lambda e: (-ranked[e], e))
    return ordered[:MAX_EMAILS]