import asyncio

from app.scan.seo_checker import _analyze_page_seo


def test_seo_missing_title() -> None:
    rows = _analyze_page_seo("https://x.ru/", "<html><body></body></html>")
    codes = {r.get("penalty_code") for r in rows}
    assert "seo_missing_title" in codes


def test_seo_noindex_home() -> None:
    html = (
        '<html><head><title>Ok title here enough length</title>'
        '<meta name="robots" content="noindex"></head><body></body></html>'
    )
    rows = _analyze_page_seo("https://x.ru/", html)
    assert any(r.get("penalty_code") == "seo_noindex_home" for r in rows)