from app.compliance.policy_content import analyze_privacy_policy_text


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