"""Строгость поиска политики ПДн — без ложных срабатываний на лендинги."""

from app.compliance.privacy_detection import (
    _main_page_has_privacy_signal,
    _page_content_is_privacy_policy,
    collect_privacy_candidate_urls,
)

LANDING_152_MARKETING = """
<html><head>
<meta name="description" content="Риски штрафов по 152-ФЗ и технические сигналы."/>
<title>Проверка сайта — 152-ФЗ</title>
</head><body>
<p>До 15 страниц сайта и типовые адреса политики ПДн.</p>
<p>Уязвимости и риски штрафов по 152-ФЗ</p>
</body></html>
"""

POLICY_PAGE = """
<html><body>
<h1>Политика конфиденциальности</h1>
<p>Оператор обрабатывает персональные данные. Цели обработки указаны ниже.
Субъект персональных данных вправе отозвать согласие. Роскомнадзор.</p>
""" + ("Текст политики. " * 80) + """
</body></html>
"""

PAGE_WITH_LINK = """
<html><body>
<a href="/politika-konfidencialnosti">Политика конфиденциальности</a>
</body></html>
"""


def test_landing_152_not_policy():
    assert not _main_page_has_privacy_signal(LANDING_152_MARKETING)
    assert not _page_content_is_privacy_policy(LANDING_152_MARKETING)
    urls = collect_privacy_candidate_urls("https://example.com/", LANDING_152_MARKETING)
    assert not any("/politika" in u for u in urls) or all(
        "politika-konfid" in u or "privacy" in u for u in urls
    )


def test_policy_document_detected():
    assert _page_content_is_privacy_policy(POLICY_PAGE)


def test_real_policy_link():
    assert _main_page_has_privacy_signal(PAGE_WITH_LINK)
    candidates = collect_privacy_candidate_urls("https://shop.ru/", PAGE_WITH_LINK)
    assert any("politika-konfidencialnosti" in u for u in candidates)