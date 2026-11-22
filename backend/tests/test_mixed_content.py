from app.scan.mixed_content import find_mixed_content_urls


def test_mixed_content_detected() -> None:
    html = '<img src="http://cdn.example.com/a.png" />'
    urls = find_mixed_content_urls("https://site.ru/", html)
    assert len(urls) == 1
    assert urls[0].startswith("http://")


def test_https_only_ignored() -> None:
    html = '<img src="https://cdn.example.com/a.png" />'
    assert find_mixed_content_urls("https://site.ru/", html) == []


def test_http_page_skipped() -> None:
    html = '<img src="http://cdn.example.com/a.png" />'
    assert find_mixed_content_urls("http://site.ru/", html) == []