from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.scan.fetch import PageFetchResult, fetch_target_page

CONTACT_FALLBACK_PATHS = (
    "/contacts/",
    "/contacts",
    "/contact/",
    "/contact",
    "/kontakty/",
    "/kontakty",
    "/about/contacts/",
    "/company/contacts/",
    "/info/contacts/",
)

BOT_WALL_MARKERS = (
    "captcha",
    "cf-challenge",
    "ddos-guard",
    "servicepipe",
    "qrator",
    "checking your browser",
    "access denied",
    "доступ ограничен",
    "подтвердите, что вы не робот",
    "антибот",
    "antibot",
    "challenge-platform",
    "__cf_chl",
)


@dataclass(slots=True)
class ScanPageFetch:
    requested_url: str
    fetched_url: str
    result: PageFetchResult
    tried_urls: list[str] = field(default_factory=list)
    used_fallback: bool = False

    @property
    def html(self) -> str | None:
        return self.result.html

    @property
    def html_available(self) -> bool:
        return self.result.html_available and not looks_like_bot_wall(
            self.result.html, self.result.status_code
        )


def looks_like_bot_wall(html: str | None, status_code: int | None) -> bool:
    if status_code in (403, 429, 503):
        return True
    if not html:
        return False
    lower = html.lower()
    return any(marker in lower for marker in BOT_WALL_MARKERS)


def _is_contact_path(path: str) -> bool:
    lower = path.lower().rstrip("/")
    for suffix in ("contact", "contacts", "kontakty"):
        if lower.endswith(suffix) or f"/{suffix}" in lower:
            return True
    return False


def _fallback_urls(requested: str) -> list[str]:
    parsed = urlparse(requested)
    if _is_contact_path(parsed.path or "/"):
        return []
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls: list[str] = []
    seen: set[str] = {requested.rstrip("/")}
    for path in CONTACT_FALLBACK_PATHS:
        candidate = urljoin(origin + "/", path.lstrip("/"))
        key = candidate.rstrip("/")
        if key not in seen:
            seen.add(key)
            urls.append(candidate)
    return urls


async def fetch_for_scan(requested_url: str) -> ScanPageFetch:
    tried: list[str] = [requested_url]
    primary = await fetch_target_page(requested_url)
    if primary.html_available and not looks_like_bot_wall(primary.html, primary.status_code):
        return ScanPageFetch(
            requested_url=requested_url,
            fetched_url=requested_url,
            result=primary,
            tried_urls=tried,
        )

    for alt in _fallback_urls(requested_url):
        tried.append(alt)
        alt_result = await fetch_target_page(alt)
        if alt_result.html_available and not looks_like_bot_wall(
            alt_result.html, alt_result.status_code
        ):
            return ScanPageFetch(
                requested_url=requested_url,
                fetched_url=alt,
                result=alt_result,
                tried_urls=tried,
                used_fallback=True,
            )

    return ScanPageFetch(
        requested_url=requested_url,
        fetched_url=requested_url,
        result=primary,
        tried_urls=tried,
    )