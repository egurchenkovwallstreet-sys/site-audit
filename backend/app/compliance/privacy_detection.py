from __future__ import annotations

import re
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

# Путь/URL — только устойчивые фрагменты (без «152», «пдн», «обработк» в одиночку).
PRIVACY_HREF_MARKERS = (
    "privacy",
    "confidential",
    "personal-data",
    "personal_data",
    "personaldata",
    "pd-policy",
    "data-protection",
    "politika",
    "konfid",
    "конфид",
    "pdn",
    "legal/priv",
    "policy-privacy",
    "privacy-policy",
    "privacy_policy",
    "politika-konfid",
    "politika_konfid",
    "politika-konf",
    "confidencial",
    "legal-documents",
    "konfidencialnosti",
)

PRIVACY_LINK_LABEL_MARKERS = (
    "политика конфиденциальности",
    "политика в отношении обработки",
    "политика обработки персональных",
    "обработк персональн",
    "privacy policy",
    "personal data policy",
)

PRIVACY_TEXT_PHRASES = (
    "политика конфиденциальности",
    "политика в отношении обработки персональных",
    "политика обработки персональных",
    "privacy policy",
    "обработка персональных данных",
)

POLICY_LEGAL_WORDS = (
    "оператор",
    "субъект персональных",
    "субъект пдн",
    "цели обработки",
    "согласие субъекта",
    "роскомнадзор",
    "ркн",
    "права субъекта",
)

COMMON_PRIVACY_PATHS = (
    "/privacy",
    "/offer",
    "/public-offer",
    "/legal-documents/politika_konfidencialnosti_0/",
    "/legal-documents/politika_konfidencialnosti_0",
    "/legal-documents/",
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
    r'href\s*=\s*["\']([^"\']*(?:privacy|konfid|конфид|personal|pdn|politika|legal-documents)[^"\']*)["\']',
    re.IGNORECASE,
)

_RAW_PRIVACY_IN_SOURCE = re.compile(
    r"(?:https?://[^\s\"'<>]+)?/?legal-documents/[\w_-]*konfid[\w_-]*|politika[_-]konfidencialnosti[\w_-]*",
    re.IGNORECASE,
)

MAX_EXTRA_FETCHES = 12


def _same_origin(base: str, target: str) -> bool:
    b = urlparse(base)
    t = urlparse(target)
    return b.scheme == t.scheme and b.netloc.lower() == t.netloc.lower()


def _href_suggests_privacy(href: str) -> bool:
    if not href or href.strip() in ("#", "/", ""):
        return False
    blob = unquote(href).lower()
    return any(h in blob for h in PRIVACY_HREF_MARKERS)


def _link_suggests_privacy(href: str, label: str) -> bool:
    """Совместимость: ссылка на документ, не маркетинговый текст."""
    if _href_suggests_privacy(href):
        return True
    label_l = label.lower()
    return any(m in label_l for m in PRIVACY_LINK_LABEL_MARKERS) and bool(href.strip())


def _anchor_points_to_policy(page_url: str, href: str, label: str) -> str | None:
    if not _link_suggests_privacy(href, label):
        return None
    full = urljoin(page_url, href.strip())
    if not full.startswith(("http://", "https://")):
        return None
    if not _same_origin(page_url, full):
        return None
    return full.split("#")[0].rstrip("/")


def _raw_html_mentions_privacy_url(page_url: str, html: str) -> bool:
    """Явный URL политики в разметке (SPA, JSON), не разговор о 152-ФЗ."""
    blob = unquote(html).lower()
    if _RAW_PRIVACY_IN_SOURCE.search(blob):
        return True
    return "legal-documents" in blob and "konfid" in blob


def _privacy_urls_in_raw(page_url: str, html: str) -> list[str]:
    blob = unquote(html)
    found: list[str] = []
    seen: set[str] = set()
    for m in _RAW_PRIVACY_IN_SOURCE.finditer(blob):
        fragment = m.group(0)
        if fragment.startswith("http"):
            full = fragment.split()[0].rstrip(".,;")
        else:
            full = urljoin(page_url, fragment if fragment.startswith("/") else f"/{fragment}")
        key = full.split("#")[0].rstrip("/")
        if _same_origin(page_url, key) and key not in seen:
            seen.add(key)
            found.append(key)
    return found


_SITEMAP_LOC = re.compile(r"<loc>\s*([^<]+)\s*</loc>", re.IGNORECASE)


def privacy_urls_from_sitemap(page_url: str, sitemap_xml: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _SITEMAP_LOC.finditer(sitemap_xml):
        candidate = match.group(1).strip()
        if not candidate.startswith("http"):
            candidate = urljoin(page_url, candidate)
        if not _same_origin(page_url, candidate):
            continue
        if not _href_suggests_privacy(candidate):
            continue
        key = candidate.split("#")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            urls.append(key)
    return urls


def privacy_urls_from_robots(page_url: str, robots_txt: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for line in robots_txt.splitlines():
        lower = line.lower()
        if "konfid" not in lower and "legal-documents" not in lower and "privacy" not in lower:
            continue
        for part in line.split():
            if not part.startswith("http") and "/" not in part:
                continue
            candidate = part if part.startswith("http") else urljoin(page_url, part)
            if not _same_origin(page_url, candidate):
                continue
            if not _href_suggests_privacy(candidate):
                continue
            key = candidate.split("#")[0].rstrip("/")
            if key not in seen:
                seen.add(key)
                urls.append(key)
    return urls


def _main_page_has_privacy_signal(html: str) -> bool:
    """Есть ли явная ссылка на политику (не meta и не «слова про ПДн» на лендинге)."""
    soup = BeautifulSoup(html, "html.parser")
    page_url = ""
    base = soup.find("base", href=True)
    if base:
        page_url = base.get("href", "")

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = a.get_text(" ", strip=True)
        if _link_suggests_privacy(href, label):
            return True

    for match in _HREF_IN_HTML.finditer(html):
        if _href_suggests_privacy(match.group(1)):
            return True

    return False


def policy_link_targets(page_url: str, html: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        label = a.get_text(" ", strip=True)
        target = _anchor_points_to_policy(page_url, href, label)
        if target and target not in seen:
            seen.add(target)
            urls.append(target)
    for match in _HREF_IN_HTML.finditer(html):
        fragment = match.group(1)
        if not _href_suggests_privacy(fragment):
            continue
        full = urljoin(page_url, fragment)
        key = full.split("#")[0].rstrip("/")
        if _same_origin(page_url, key) and key not in seen:
            seen.add(key)
            urls.append(key)
    return urls


def _page_content_is_privacy_policy(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    if len(text) < 500:
        return False
    hits = sum(1 for p in PRIVACY_TEXT_PHRASES if p in text)
    if hits >= 2:
        return True
    if hits >= 1 and sum(1 for w in POLICY_LEGAL_WORDS if w in text) >= 2:
        return True
    return False


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

    for target in policy_link_targets(page_url, html):
        add(target)

    for path in COMMON_PRIVACY_PATHS:
        add(path)

    for extra in _privacy_urls_in_raw(page_url, html):
        add(extra)

    return ordered