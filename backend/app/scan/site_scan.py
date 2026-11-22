from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.compliance.privacy_detection import policy_urls_from_antibot_challenge
from app.scan.fetch import PageFetchResult, fetch_target_page
from app.scan.page_fetch import (
    CONTACT_FALLBACK_PATHS,
    ScanPageFetch,
    fetch_for_scan,
    page_is_readable,
)
from app.scan.playwright_fetch import PlaywrightFetchBudget, fetch_target_page_smart
from app.scan.site_pages import (
    LEGAL_SEED_PATHS,
    MAX_SCAN_PAGES,
    plan_scan_page_urls,
    sitemap_page_urls,
)


@dataclass(slots=True)
class ScannedPage:
    url: str
    html: str
    result: PageFetchResult
    via_playwright: bool = False


@dataclass(slots=True)
class SiteScanBundle:
    requested_url: str
    entry: ScanPageFetch
    pages: list[ScannedPage] = field(default_factory=list)
    browser_budget: PlaywrightFetchBudget = field(
        default_factory=PlaywrightFetchBudget.disabled
    )

    @property
    def html_available(self) -> bool:
        if page_is_readable(self.entry.html, self.entry.result.status_code):
            return True
        return any(
            page_is_readable(p.html, p.result.status_code) for p in self.pages
        )

    @property
    def page_pairs(self) -> list[tuple[str, str]]:
        return [(p.url, p.html) for p in self.pages]


def _site_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def _bootstrap_pages_via_browser(
    base_url: str,
    entry: ScanPageFetch,
    *,
    budget: PlaywrightFetchBudget,
    max_pages: int,
) -> list[ScannedPage]:
    if not budget.enabled or budget.remaining <= 0:
        return []

    origin = _site_origin(base_url)
    candidates: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        key = url.rstrip("/")
        if key not in seen:
            seen.add(key)
            candidates.append(url)

    if entry.html:
        for url in policy_urls_from_antibot_challenge(entry.html, entry.fetched_url):
            add(url)
    for path in LEGAL_SEED_PATHS:
        add(urljoin(origin + "/", path.lstrip("/")))
    for path in CONTACT_FALLBACK_PATHS:
        add(urljoin(origin + "/", path.lstrip("/")))
    add(base_url)

    pages: list[ScannedPage] = []
    for url in candidates:
        if len(pages) >= max_pages:
            break
        res = await fetch_target_page_smart(url, budget)
        if not page_is_readable(res.html, res.status_code):
            continue
        pages.append(
            ScannedPage(
                url=url,
                html=res.html or "",
                result=res,
                via_playwright=url in budget.used_urls,
            )
        )
    return pages


async def fetch_scan_site(
    requested_url: str,
    *,
    max_pages: int = MAX_SCAN_PAGES,
) -> SiteScanBundle:
    budget = PlaywrightFetchBudget.from_settings()
    entry = await fetch_for_scan(requested_url, budget=budget)

    if not page_is_readable(entry.html, entry.result.status_code):
        boot = await _bootstrap_pages_via_browser(
            requested_url,
            entry,
            budget=budget,
            max_pages=max_pages,
        )
        if boot:
            lead = boot[0]
            promoted = ScanPageFetch(
                requested_url=requested_url,
                fetched_url=lead.url,
                result=lead.result,
                tried_urls=entry.tried_urls + [p.url for p in boot],
                used_fallback=entry.used_fallback,
                used_playwright=True,
            )
            return SiteScanBundle(
                requested_url=requested_url,
                entry=promoted,
                pages=boot,
                browser_budget=budget,
            )
        return SiteScanBundle(
            requested_url=requested_url,
            entry=entry,
            pages=[],
            browser_budget=budget,
        )

    entry_html = entry.html or ""
    entry_url = entry.fetched_url

    sitemap_extra: list[str] = []
    sm = await fetch_target_page(urljoin(entry_url, "/sitemap.xml"))
    if sm.html and len(sm.html) < 2_000_000:
        sitemap_extra = sitemap_page_urls(entry_url, sm.html, limit=30)

    plan = plan_scan_page_urls(
        entry_url,
        entry_html,
        extra_urls=sitemap_extra,
        max_pages=max_pages,
    )

    pages: list[ScannedPage] = []
    for url in plan:
        if url.rstrip("/") == entry_url.rstrip("/"):
            pages.append(
                ScannedPage(
                    entry_url,
                    entry_html,
                    entry.result,
                    via_playwright=entry.used_playwright,
                )
            )
            continue
        res = await fetch_target_page(url)
        via_pw = False
        if not page_is_readable(res.html, res.status_code):
            smart = await fetch_target_page_smart(url, budget)
            if not page_is_readable(smart.html, smart.status_code):
                continue
            res = smart
            via_pw = url in budget.used_urls
        pages.append(ScannedPage(url, res.html or "", res, via_playwright=via_pw))

    if not pages:
        pages.append(
            ScannedPage(
                entry_url,
                entry_html,
                entry.result,
                via_playwright=entry.used_playwright,
            )
        )

    return SiteScanBundle(
        requested_url=requested_url,
        entry=entry,
        pages=pages[:max_pages],
        browser_budget=budget,
    )