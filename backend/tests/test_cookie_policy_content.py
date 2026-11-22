from app.compliance.cookie_policy_content import (
    analyze_cookie_policy_text,
    extract_cookie_policy_text,
    privacy_policy_covers_cookies,
)


def test_privacy_policy_covers_cookies_ok() -> None:
    text = (
        "Политика. Мы используем файлы cookie. "
        "Аналитические cookie нужны для статистики посещений. "
        "Вы можете отключить cookie в настройках браузера или отказаться от согласия."
        * 5
    )
    assert privacy_policy_covers_cookies(text)


def test_cookie_policy_incomplete_flags() -> None:
    text = "Мы используем cookie на сайте. " * 30
    result = analyze_cookie_policy_text(text, source="test")
    assert result.analyzed
    assert len(result.missing_labels) >= 2


def test_extract_prefers_cookie_url() -> None:
    pages = [
        ("https://x.ru/", "<p>куки " * 50 + "аналитика отказ браузер</p>"),
        (
            "https://x.ru/cookie-policy",
            "<p>cookie политика " * 40 + "аналитика отключить браузер</p>",
        ),
    ]
    body, url = extract_cookie_policy_text(pages)
    assert url is not None
    assert "cookie-policy" in url
    assert body is not None