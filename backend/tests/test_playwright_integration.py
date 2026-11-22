"""Интеграция Playwright в цепочку fetch (без запуска реального Chromium)."""

import pytest

from app.scan.fetch import PageFetchResult
from app.scan.page_fetch import fetch_for_scan, page_is_readable
from app.scan.playwright_fetch import PlaywrightFetchBudget, fetch_target_page_smart

READABLE_HTML = "<html><body>" + ("Нормальная страница. " * 40) + "</body></html>"
ANTIBOT_HTML = '<html><div class="captcha-delivery">challenge</div></html>'
POLICY_HTML = """
<html><body>
<h1>Политика конфиденциальности</h1>
<p>Оператор обрабатывает персональные данные. Цели обработки указаны ниже.
Субъект персональных данных вправе отозвать согласие. Роскомнадзор.</p>
""" + ("Текст политики. " * 80) + """
</body></html>
"""


@pytest.mark.asyncio
async def test_fetch_for_scan_uses_playwright_after_antibot(monkeypatch):
    calls: list[str] = []

    async def fake_http(url: str) -> PageFetchResult:
        calls.append(f"http:{url}")
        return PageFetchResult(
            status_code=200,
            html=ANTIBOT_HTML,
            headers={},
            ssl_verify_fallback=False,
            fetch_error=None,
        )

    async def fake_browser(url: str) -> PageFetchResult:
        calls.append(f"browser:{url}")
        return PageFetchResult(
            status_code=200,
            html=READABLE_HTML,
            headers={},
            ssl_verify_fallback=False,
            fetch_error=None,
        )

    monkeypatch.setattr("app.scan.page_fetch.fetch_target_page", fake_http)
    monkeypatch.setattr(
        "app.scan.playwright_fetch.fetch_page_with_browser", fake_browser
    )
    budget = PlaywrightFetchBudget(3, enabled=True)
    entry = await fetch_for_scan("https://blocked.example/", budget=budget)

    assert entry.used_playwright
    assert page_is_readable(entry.html, entry.result.status_code)
    assert any(c.startswith("browser:") for c in calls)


@pytest.mark.asyncio
async def test_smart_fetch_skips_browser_when_http_ok(monkeypatch):
    async def fake_http(url: str) -> PageFetchResult:
        return PageFetchResult(200, READABLE_HTML, {}, False, None)

    async def fail_browser(url: str) -> PageFetchResult:
        raise AssertionError("browser should not run")

    monkeypatch.setattr("app.scan.playwright_fetch.fetch_target_page", fake_http)
    monkeypatch.setattr(
        "app.scan.playwright_fetch.fetch_page_with_browser", fail_browser
    )
    budget = PlaywrightFetchBudget(2, enabled=True)
    res = await fetch_target_page_smart("https://example.com/", budget)
    assert budget.remaining == 2
    assert page_is_readable(res.html, res.status_code)


@pytest.mark.asyncio
async def test_smart_fetch_policy_via_browser(monkeypatch):
    async def fake_http(url: str) -> PageFetchResult:
        return PageFetchResult(200, ANTIBOT_HTML, {}, False, None)

    async def fake_browser(url: str) -> PageFetchResult:
        return PageFetchResult(200, POLICY_HTML, {}, False, None)

    monkeypatch.setattr("app.scan.playwright_fetch.fetch_target_page", fake_http)
    monkeypatch.setattr(
        "app.scan.playwright_fetch.fetch_page_with_browser", fake_browser
    )
    budget = PlaywrightFetchBudget(1, enabled=True)
    res = await fetch_target_page_smart(
        "https://cian.example/legal-documents/privacy/", budget
    )
    assert budget.remaining == 0
    assert "политика конфиденциальности" in (res.html or "").lower()