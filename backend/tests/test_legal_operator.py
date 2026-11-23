from app.compliance.legal_operator import html_has_operator_requisites


def test_inn_in_html():
    html = "<html><body><p>ООО Рога. ИНН 7701234567. ОГРН 1027700000000</p></body></html>"
    assert html_has_operator_requisites(html)


def test_no_requisites():
    html = "<html><body><p>Красивый салон. Запишитесь online.</p></body></html>"
    assert not html_has_operator_requisites(html)


def test_flutter_bundle_unicode_escapes():
    # Как в darom-app.online/main.dart.js — кириллица в \uXXXX
    bundle = (
        r"\u0418\u041d\u041d: 544600448560\n"
        r"\u041e\u0413\u0420\u041d/\u041e\u0413\u0420\u041d\u0418\u041f: "
        r"322547600082793"
    )
    assert html_has_operator_requisites(bundle)


def test_darom_style_operator_line():
    raw = (
        "Юлия Викторовна\nИНН: 544600448560\n"
        "ОГРН/ОГРНИП: 322547600082793\nКонтактный телефон"
    )
    assert html_has_operator_requisites(raw)