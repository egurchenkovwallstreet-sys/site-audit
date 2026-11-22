from app.scan.email_discover import discover_contact_emails


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