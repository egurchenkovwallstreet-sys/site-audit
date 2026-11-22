from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scan.playwright_fetch import PlaywrightFetchBudget
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

# Только явные признаки страницы-заглушки (не слово «антибот» в тексте политики).
HARD_BOT_MARKERS = (
    "cf-challenge",
    "challenge-platform",
    "__cf_chl",
    "cdn-cgi/challenge",
    "checking your browser",
    "g-recaptcha",
    "hcaptcha.com",
    "captcha-delivery",
    "interstitial",
)

SOFT_BOT_MARKERS = (
    "подтвердите, что вы не робот",
    "доступ ограничен",
    "access denied",
    "please enable javascript",
)


@dataclass(slots=True)
class ScanPageFetch:
    requested_url: str
    fetched_url: str
    result: PageFetchResult
    tried_urls: list[str] = field(default_factory=list)
    used_fallback: bool = False
    used_playwright: bool = False

    @property
    def html(self) -> str | None:
        return self.result.html

    @property
    def html_available(self) -> bool:
        return page_is_readable(self.result.html, self.result.status_code)


def page_is_readable(html: str | None, status_code: int | None) -> bool:
    if status_code is not None and status_code >= 400:
        return False
    if status_code in (403, 429, 503):
        return False
    if not html or len(html.strip()) < 80:
        return False
    return not looks_like_bot_wall(html, status_code)


def looks_like_bot_wall(html: str | None, status_code: int | None) -> bool:
    if status_code in (403, 429, 503):
        return True
    if not html:
        return False
    text = html.strip()
    if len(text) < 80:
        return True
    lower = html.lower()
    head = lower[:4000]
    if any(marker in lower for marker in HARD_BOT_MARKERS):
        return True
    if len(text) < 5000 and any(marker in head for marker in SOFT_BOT_MARKERS):
        return True
    if len(text) < 3500 and "captcha" in head and "<form" in head:
        return True
    return False


def fetch_block_reason(html: str | None, status_code: int | None) -> str:
    if status_code in (403, 429, 503):
        return "http_block"
    if not html or len(html.strip()) < 80:
        return "empty_body"
    if looks_like_bot_wall(html, status_code):
        return "antibot"
    if status_code is not None and status_code >= 400:
        return "http_error"
    return "unknown"


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


async def fetch_for_scan(
    requested_url: str,
    *,
    budget: PlaywrightFetchBudget | None = None,
) -> ScanPageFetch:
    tried: list[str] = [requested_url]
    primary = await fetch_target_page(requested_url)

    if page_is_readable(primary.html, primary.status_code):
        return ScanPageFetch(
            requested_url=requested_url,
            fetched_url=requested_url,
            result=primary,
            tried_urls=tried,
        )

    for alt in _fallback_urls(requested_url):
        tried.append(alt)
        alt_result = await fetch_target_page(alt)
        if page_is_readable(alt_result.html, alt_result.status_code):
            return ScanPageFetch(
                requested_url=requested_url,
                fetched_url=alt,
                result=alt_result,
                tried_urls=tried,
                used_fallback=True,
            )

    if budget is not None and budget.enabled:
        from app.scan.playwright_fetch import fetch_target_page_smart

        for candidate in (requested_url, *_fallback_urls(requested_url)):
            tried.append(candidate)
            smart = await fetch_target_page_smart(candidate, budget)
            if page_is_readable(smart.html, smart.status_code):
                return ScanPageFetch(
                    requested_url=requested_url,
                    fetched_url=candidate,
                    result=smart,
                    tried_urls=tried,
                    used_fallback=candidate.rstrip("/")
                    != requested_url.rstrip("/"),
                    used_playwright=True,
                )

    return ScanPageFetch(
        requested_url=requested_url,
        fetched_url=requested_url,
        result=primary,
        tried_urls=tried,
    )