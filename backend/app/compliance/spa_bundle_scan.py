from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.compliance.form_consent import script_url_is_vendor_bundle
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
_PRIVACY_ROUTE = re.compile(r'["\']/(?:privacy|offer)["\']', re.IGNORECASE)


@dataclass(slots=True)
class SpaBundleScan:
    privacy_found: bool = False
    privacy_script_url: str | None = None
    consent_found: bool = False
    consent_script_url: str | None = None


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


def _body_has_privacy(body: str) -> bool:
    if _PRIVACY_ROUTE.search(body):
        return True
    lower = body.lower()
    if "privacy_policy" in lower or "politika_konfid" in lower:
        return True
    if "legal-documents" in lower and "konfid" in lower:
        return True
    return (
        "политик" in lower
        and ("конфиденциальн" in lower or "персональн" in lower)
        and len(body) > 800
    )


async def analyze_spa_bundles(page_url: str, html: str) -> SpaBundleScan:
    """Один проход по JS-бандлам: политика и согласие без повторных загрузок."""
    result = SpaBundleScan()
    for script_url in _discover_script_urls(page_url, html):
        body = await fetch_resource_text(script_url, max_bytes=MAX_SCRIPT_BYTES)
        if not body:
            continue
        if not result.privacy_found and _body_has_privacy(body):
            result.privacy_found = True
            result.privacy_script_url = script_url
        if (
            not result.consent_found
            and not script_url_is_vendor_bundle(script_url)
            and _text_has_marker(body, SPA_CONSENT_MARKERS)
        ):
            result.consent_found = True
            result.consent_script_url = script_url
        if result.privacy_found and result.consent_found:
            break
    return result