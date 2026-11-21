from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from app.scan.fetch import PageFetchResult, fetch_target_page
from app.scan.page_fetch import ScanPageFetch, fetch_for_scan, looks_like_bot_wall
from app.scan.site_pages import MAX_SCAN_PAGES, plan_scan_page_urls, sitemap_page_urls


@dataclass(slots=True)
class ScannedPage:
    url: str
    html: str
    result: PageFetchResult


@dataclass(slots=True)
class SiteScanBundle:
    requested_url: str
    entry: ScanPageFetch
    pages: list[ScannedPage] = field(default_factory=list)

    @property
    def html_available(self) -> bool:
        return self.entry.html_available

    @property
    def page_pairs(self) -> list[tuple[str, str]]:
        return [(p.url, p.html) for p in self.pages]


async def fetch_scan_site(
    requested_url: str,
    *,
    max_pages: int = MAX_SCAN_PAGES,
) -> SiteScanBundle:
    entry = await fetch_for_scan(requested_url)
    if not entry.html_available or not entry.html:
        return SiteScanBundle(requested_url=requested_url, entry=entry, pages=[])

    entry_html = entry.html
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
            pages.append(ScannedPage(entry_url, entry_html, entry.result))
            continue
        res = await fetch_target_page(url)
        if not res.html_available or not res.html:
            continue
        if looks_like_bot_wall(res.html, res.status_code):
            continue
        pages.append(ScannedPage(url, res.html, res))

    if not pages:
        pages.append(ScannedPage(entry_url, entry_html, entry.result))

    return SiteScanBundle(requested_url=requested_url, entry=entry, pages=pages[:max_pages])