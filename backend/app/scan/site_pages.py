from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.compliance.privacy_detection import _same_origin

MAX_SCAN_PAGES = 15
SITEMAP_LOC = re.compile(r"<loc>\s*([^<]+)\s*</loc>", re.IGNORECASE)

SKIP_SUFFIXES = (
    ".pdf",
    ".zip",
    ".rar",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".css",
    ".js",
    ".xml",
    ".mp4",
    ".woff",
    ".woff2",
)

LINK_PRIORITY_HINTS = (
    "privacy",
    "politik",
    "конфид",
    "personal",
    "pdn",
    "legal",
    "152",
    "cookie",
    "soglas",
    "consent",
    "contact",
    "kontakt",
    "about",
    "company",
    "offer",
    "terms",
    "policy",
    "пдн",
    "персональн",
    "политик",
    "соглас",
    "контакт",
    "о-компании",
    "реквизит",
)


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _normalize_page_url(base: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None
    full = urljoin(base, href).split("#")[0]
    if not _same_origin(base, full):
        return None
    path = urlparse(full).path.lower()
    if any(path.endswith(s) for s in SKIP_SUFFIXES):
        return None
    return full.rstrip("/") or full


def _score_link(url: str, anchor: str) -> int:
    blob = f"{url} {anchor}".lower()
    score = 0
    for hint in LINK_PRIORITY_HINTS:
        if hint in blob:
            score += 8
    path = urlparse(url).path
    depth = path.count("/")
    score -= min(depth, 5)
    return score


def discover_internal_links(page_url: str, html: str, *, limit: int = 40) -> list[str]:
    """Ссылки с одной страницы (как с главной), с приоритетом юридических разделов."""
    soup = BeautifulSoup(html, "html.parser")
    scored: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        full = _normalize_page_url(page_url, a.get("href", ""))
        if not full:
            continue
        label = a.get_text(" ", strip=True)
        key = full.rstrip("/")
        score = _score_link(full, label)
        scored[key] = max(scored.get(key, 0), score)

    ordered = sorted(scored.items(), key=lambda item: (-item[1], item[0]))
    return [url for url, _ in ordered[:limit]]


def sitemap_page_urls(site_url: str, sitemap_xml: str, *, limit: int = 40) -> list[str]:
    origin = _origin(site_url)
    urls: list[str] = []
    seen: set[str] = set()
    for match in SITEMAP_LOC.finditer(sitemap_xml):
        candidate = match.group(1).strip()
        if not candidate.startswith("http"):
            candidate = urljoin(origin + "/", candidate.lstrip("/"))
        if not _same_origin(site_url, candidate):
            continue
        path = urlparse(candidate).path.lower()
        if any(path.endswith(s) for s in SKIP_SUFFIXES):
            continue
        key = candidate.rstrip("/")
        if key not in seen:
            seen.add(key)
            urls.append(key)
        if len(urls) >= limit:
            break
    return urls


def plan_scan_page_urls(
    entry_url: str,
    entry_html: str,
    *,
    extra_urls: list[str] | None = None,
    max_pages: int = MAX_SCAN_PAGES,
) -> list[str]:
    """До max_pages URL: точка входа + ссылки со страницы + sitemap/доп."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(url: str) -> None:
        key = url.rstrip("/")
        if key not in seen:
            seen.add(key)
            ordered.append(url if url.endswith("/") or "." in urlparse(url).path else key)

    add(entry_url)
    for link in discover_internal_links(entry_url, entry_html):
        add(link)
        if len(ordered) >= max_pages:
            return ordered[:max_pages]
    for link in extra_urls or []:
        if _same_origin(entry_url, link):
            add(link)
            if len(ordered) >= max_pages:
                return ordered[:max_pages]
    return ordered[:max_pages]