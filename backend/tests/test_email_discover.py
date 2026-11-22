import pytest

from app.scan.email_discover import (
    discover_contact_emails,
    discover_contact_emails_for_site,
)


def test_mailto_and_text():
    html = """
    <html><body>
    <a href="mailto:info@shop.ru">Почта</a>
    <p>Связь: sales@shop.ru</p>
    </body></html>
    """
    emails = discover_contact_emails(
        [("https://shop.ru/contacts", html)],
        site_url="https://shop.ru/",
    )
    assert "info@shop.ru" in emails
    assert "sales@shop.ru" in emails


def test_filters_junk():
    html = '<a href="mailto:noreply@shop.ru">x</a><p>test@example.com</p>'
    emails = discover_contact_emails([("https://shop.ru/", html)])
    assert emails == []


@pytest.mark.asyncio
async def test_policy_page_fetched_for_email(monkeypatch):
    home = "<html><body><a href='/politika'>Политика</a></body></html>"
    policy = (
        "<html><body><h1>Политика</h1><p>Оператор: legal@shop.ru</p>"
        + (" Текст. " * 30)
        + "</body></html>"
    )

    async def fake_fetch(url: str):
        from app.scan.fetch import PageFetchResult

        if "politik" in url:
            return PageFetchResult(200, policy, {}, False, None)
        return PageFetchResult(200, home, {}, False, None)

    monkeypatch.setattr("app.scan.email_discover.fetch_target_page", fake_fetch)
    emails = await discover_contact_emails_for_site(
        "https://shop.ru/",
        "https://shop.ru/",
        home,
        [("https://shop.ru/", home)],
    )
    assert "legal@shop.ru" in emails