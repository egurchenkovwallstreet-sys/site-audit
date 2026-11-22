from app.compliance.legal_operator import html_has_operator_requisites


def test_inn_in_html():
    html = "<html><body><p>ООО Рога. ИНН 7701234567. ОГРН 1027700000000</p></body></html>"
    assert html_has_operator_requisites(html)


def test_no_requisites():
    html = "<html><body><p>Красивый салон. Запишитесь online.</p></body></html>"
    assert not html_has_operator_requisites(html)