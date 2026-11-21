from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Ссылки и пути, характерные для политики ПДн
PRIVACY_LINK_HINTS = (
    "privacy",
    "confidential",
    "personal-data",
    "personal_data",
    "personaldata",
    "pdn",
    "pd-policy",
    "data-protection",
    "politika",
    "konfid",
    "конфид",
    "персональн",
    "обработк",
    "152",
    "legal/priv",
    "policy-privacy",
    "privacy-policy",
    "privacy_policy",
    "politika-konfid",
    "politika_konfid",
    "politika-konf",
    "confidencial",
)

PRIVACY_TEXT_PHRASES = (
    "политика конфиденциальности",
    "политика в отношении обработки персональных",
    "политика обработки персональных",
    "персональные данные",
    "privacy policy",
    "personal data",
    "обработка персональных данных",
)

# Типовые пути на российских и международных сайтах
COMMON_PRIVACY_PATHS = (
    "/privacy",
    "/privacy-policy",
    "/privacy_policy",
    "/politika-konfidencialnosti",
    "/politika-konfidentsialnosti",
    "/politika_konfidencialnosti",
    "/politika-obrabotki-personalnyh-dannyh",
    "/confidential",
    "/confidentiality",
    "/personal-data",
    "/personal_data",
    "/legal/privacy",
    "/legal/privacy-policy",
    "/docs/privacy",
    "/pages/privacy",
    "/info/privacy",
    "/about/privacy",
    "/pdn",
    "/pd-policy",
)

_HREF_IN_HTML = re.compile(
    r'href\s*=\s*["\']([^"\']*(?:privacy|konfid|конфид|personal|pdn|152|politika)[^"\']*)["\']',
    re.IGNORECASE,
)

MAX_EXTRA_FETCHES = 10


def _same_origin(base: str, target: str) -> bool:
    b = urlparse(base)
    t = urlparse(target)
    return b.scheme == t.scheme and b.netloc.lower() == t.netloc.lower()


def _link_suggests_privacy(href: str, label: str) -> bool:
    blob = f"{href} {label}".lower()
    return any(h in blob for h in PRIVACY_LINK_HINTS)


def _main_page_has_privacy_signal(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    text_blob = soup.get_text(" ", strip=True).lower()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = a.get_text(" ", strip=True)
        if _link_suggests_privacy(href, label):
            return True

    for tag in soup.find_all(["link", "meta"]):
        content = " ".join(
            str(tag.get(attr, "")) for attr in ("href", "content", "title")
        )
        if _link_suggests_privacy(content, ""):
            return True

    for match in _HREF_IN_HTML.finditer(html):
        if _link_suggests_privacy(match.group(1), ""):
            return True

    return any(p in text_blob for p in PRIVACY_TEXT_PHRASES)


def _page_content_is_privacy_policy(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    if len(text) < 400:
        return False
    hits = sum(1 for p in PRIVACY_TEXT_PHRASES if p in text)
    return hits >= 2 or (
        hits >= 1
        and any(
            w in text
            for w in (
                "оператор",
                "субъект",
                "согласие",
                "цели обработки",
                "ркн",
                "роскомнадзор",
            )
        )
    )


def collect_privacy_candidate_urls(page_url: str, html: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(raw: str) -> None:
        full = urljoin(page_url, raw.strip())
        if not full.startswith(("http://", "https://")):
            return
        if not _same_origin(page_url, full):
            return
        key = full.split("#")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            ordered.append(key)

    for path in COMMON_PRIVACY_PATHS:
        add(path)

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = a.get_text(" ", strip=True)
        if _link_suggests_privacy(href, label):
            add(href)

    for match in _HREF_IN_HTML.finditer(html):
        add(match.group(1))

    return ordered