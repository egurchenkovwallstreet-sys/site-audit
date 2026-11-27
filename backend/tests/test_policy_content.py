from app.compliance.policy_content import (
    analyze_privacy_policy_text,
    extract_policy_text_from_scan,
)
from app.compliance.spa_bundle_scan import SpaBundleScan


def test_policy_complete_enough():
    text = (
        "Политика. Оператор ООО Рога. ИНН 123. ОГРН 123. "
        "Цели обработки персональных данных: договор. "
        "Правовые основания обработки: согласие. "
        "Права субъекта: отзыв, уточнение, блокирование, уничтожение. "
        "Сроки хранения персональных данных 5 лет. "
        "Передача третьим лицам и трансграничная передача описаны. " + "x " * 200
    )
    r = analyze_privacy_policy_text(text, source="test")
    assert r.analyzed
    assert r.missing_sections == []


def test_policy_missing_rights():
    text = (
        "Оператор ИНН ОГРН наименование. Цели обработки. "
        "Правовые основания. Сроки хранения. Передача третьим лицам. "
        + "z" * 400
    )
    r = analyze_privacy_policy_text(text, source="test")
    assert r.analyzed
    assert "rights" in r.missing_sections


def test_extract_prefers_privacy_page_over_home_chunk():
    privacy_html = (
      "<html><body><h1>Политика в отношении обработки персональных данных</h1>"
      "<p>Оператор ИНН 123 ОГРН 456 наименование юридического лица.</p>"
      "<p>Цели обработки персональных данных: услуги.</p>"
      "<p>Правовые основания обработки: согласие субъекта.</p>"
      "<p>Права субъекта: отзыв, уточнение, блокирование, уничтожение.</p>"
      "<p>Сроки хранения персональных данных 3 года.</p>"
      "<p>Передача персональных данных третьим лицам и трансграничная передача.</p>"
      + ("текст " * 120)
      + "</body></html>"
    )
    home_js = (
        '"/privacy" политик конфиденциальн персональн '
        + ("x" * 5000)
    )
    spa = SpaBundleScan(
        privacy_found=True,
        privacy_script_url="https://site/_next/static/chunks/app/page-abc.js",
        privacy_script_body=home_js,
    )
    text, source = extract_policy_text_from_scan(
        [
            ("https://site/", "<html>landing 152-ФЗ политика маркетинг</html>"),
            ("https://site/privacy", privacy_html),
        ],
        spa,
    )
    assert source == "https://site/privacy"
    r = analyze_privacy_policy_text(text or "", source=source or "")
    assert r.missing_sections == []