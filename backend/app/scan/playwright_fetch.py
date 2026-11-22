from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config import get_settings
from app.scan.fetch import (
    BROWSER_USER_AGENT,
    MAX_BODY_BYTES,
    PageFetchResult,
    fetch_target_page,
)
from app.scan.page_fetch import page_is_readable

PLAYWRIGHT_NAV_TIMEOUT_MS = 45_000
PLAYWRIGHT_SETTLE_MS = 2_500

_playwright = None
_browser = None
_browser_lock = asyncio.Lock()


@dataclass
class PlaywrightFetchBudget:
    remaining: int
    used_urls: list[str] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def disabled(cls) -> PlaywrightFetchBudget:
        return cls(0, enabled=False)

    @classmethod
    def from_settings(cls) -> PlaywrightFetchBudget:
        settings = get_settings()
        if not settings.playwright_enabled:
            return cls.disabled()
        return cls(max(0, settings.playwright_max_fetches), enabled=True)


async def _ensure_chromium():
    global _playwright, _browser
    async with _browser_lock:
        if _browser is not None:
            return _browser
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        return _browser


async def fetch_page_with_browser(url: str) -> PageFetchResult:
    browser = await _ensure_chromium()
    if browser is None:
        return PageFetchResult(
            status_code=None,
            html=None,
            headers={},
            ssl_verify_fallback=False,
            fetch_error="playwright_unavailable",
        )

    context = await browser.new_context(
        user_agent=BROWSER_USER_AGENT,
        locale="ru-RU",
        extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
    )
    page = await context.new_page()
    status_code: int | None = None
    html: str | None = None
    headers: dict[str, str] = {}
    fetch_error: str | None = None
    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PLAYWRIGHT_NAV_TIMEOUT_MS,
        )
        if response is not None:
            status_code = response.status
            headers = {k.lower(): v for k, v in response.headers.items()}
        try:
            await page.wait_for_load_state("networkidle", timeout=12_000)
        except Exception:
            await page.wait_for_timeout(PLAYWRIGHT_SETTLE_MS)
        raw = await page.content()
        if len(raw.encode("utf-8", errors="ignore")) > MAX_BODY_BYTES:
            html = raw[:MAX_BODY_BYTES]
            fetch_error = "Страница обрезана по лимиту размера"
        else:
            html = raw
    except Exception as exc:
        fetch_error = str(exc)
    finally:
        await context.close()

    return PageFetchResult(
        status_code=status_code,
        html=html,
        headers=headers,
        ssl_verify_fallback=False,
        fetch_error=fetch_error,
    )


async def fetch_target_page_smart(
    url: str,
    budget: PlaywrightFetchBudget | None,
    *,
    force_browser: bool = False,
) -> PageFetchResult:
    primary = await fetch_target_page(url)
    if (
        not force_browser
        and page_is_readable(primary.html, primary.status_code)
    ):
        return primary
    if budget is None or not budget.enabled or budget.remaining <= 0:
        return primary

    budget.remaining -= 1
    budget.used_urls.append(url)
    browser_result = await fetch_page_with_browser(url)
    if page_is_readable(browser_result.html, browser_result.status_code):
        return browser_result
    if browser_result.html and (
        not primary.html or len(browser_result.html) > len(primary.html)
    ):
        return browser_result
    return primary