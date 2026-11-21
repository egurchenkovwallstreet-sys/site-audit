from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scan.fetch import MAX_SCRIPT_BYTES, fetch_resource_text

SPA_PRIVACY_MARKERS = (
    "privacy_policy",
    "privacy policy",
    "public_offer",
    "/privacy",
    "politika_konfid",
    "legal-documents",
    "политик",
    "конфиденциальн",
    "персональн",
    "пдн",
    "privacy-consent",
    "privacy_consent",
)

SPA_CONSENT_MARKERS = (
    "privacy_consent",
    "privacy_consent_at",
    "cookie",
    "consent",
    "gdpr",
    "куки",
    "соглас",
    "offer_accepted",
)

_SCRIPT_HINT = re.compile(r"\.(?:js|mjs)(?:\?|$)", re.IGNORECASE)


def _discover_script_urls(page_url: str, html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "link"]):
        src = tag.get("src") or tag.get("href") or ""
        if not src or not _SCRIPT_HINT.search(src):
            continue
        full = urljoin(page_url, src).split("#")[0]
        if full not in seen:
            seen.add(full)
            urls.append(full)
    for name in ("main.dart.js", "flutter_bootstrap.js", "main.js", "app.js", "bundle.js"):
        full = urljoin(page_url, name)
        if full not in seen:
            seen.add(full)
            urls.append(full)
    return urls


def _text_has_marker(text: str, markers: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(m in lower for m in markers)


async def spa_bundle_has_privacy(page_url: str, html: str) -> bool:
    for script_url in _discover_script_urls(page_url, html):
        body = await fetch_resource_text(script_url, max_bytes=MAX_SCRIPT_BYTES)
        if not body:
            continue
        if _text_has_marker(body, SPA_PRIVACY_MARKERS):
            return True
        if re.search(r'["\']/(?:privacy|offer)["\']', body, re.IGNORECASE):
            return True
    return False


async def spa_bundle_has_consent(page_url: str, html: str) -> bool:
    for script_url in _discover_script_urls(page_url, html):
        body = await fetch_resource_text(script_url, max_bytes=MAX_SCRIPT_BYTES)
        if body and _text_has_marker(body, SPA_CONSENT_MARKERS):
            return True
    return False