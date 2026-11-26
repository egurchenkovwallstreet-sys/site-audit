from app.models.entities import Finding, Scan, ScanStatus
from app.reports.compose import compose_extended_report, compose_short_report


def _finding(**kwargs) -> Finding:
    defaults = {
        "id": 1,
        "scan_id": 1,
        "type": "compliance",
        "severity": "medium",
        "title": "Тест",
        "description": "Описание факта.",
        "legal_article": "152-ФЗ ст. 18.1; ст. 13.11 КоАП РФ ч. 3",
        "max_penalty": 60_000,
        "color": "yellow",
        "min_level": 1,
        "remediation": "Исправьте документ.",
        "penalty_code": "no_privacy_policy",
    }
    defaults.update(kwargs)
    return Finding(**defaults)


def _scan() -> Scan:
    return Scan(
        id=42,
        target_url="https://darom-app.online/",
        status=ScanStatus.COMPLETED.value,
        context_json='{"pages_checked": 22, "privacy_found": true}',
    )


def test_short_report_sections_and_penalties():
    text = compose_short_report(
        _scan(),
        [
            _finding(),
            _finding(
                id=2,
                type="security",
                title="Открытый .git",
                penalty_code="security_git_exposed",
                max_penalty=50_000,
            ),
            _finding(id=3, type="seo", penalty_code="seo_title_short", max_penalty=None),
        ],
    )
    assert "Сводка ориентиров по штрафам" in text
    assert "₽" in text
    assert "consultant.ru" in text
    assert "Штрафы и нарушения" in text
    assert "Технические риски" in text
    assert "SEO и разметка" in text
    assert "Что сделать" not in text
    assert "Ориентиры штрафов КоАП" in text


def test_extended_report_includes_recommendations():
    text = compose_extended_report(
        _scan(),
        [
            _finding(),
            _finding(
                id=2,
                type="security",
                severity="high",
                title="Открытый .git",
                penalty_code="security_git_exposed",
                remediation="Закройте доступ к .git.",
                max_penalty=50_000,
            ),
        ],
    )
    assert "Резюме" in text
    assert "Штрафы и нарушения" in text
    assert "Подробные рекомендации" in text
    assert "Закройте доступ" in text
    assert text.index("Штрафы и нарушения") < text.index("Подробные рекомендации")