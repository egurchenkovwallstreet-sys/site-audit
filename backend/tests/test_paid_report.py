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


def test_short_report_contains_koap_and_rub():
    text = compose_short_report(_scan(), [_finding()])
    assert "consultant.ru" in text
    assert "13.11" in text
    assert "₽" in text
    assert "до 20 000" in text or "до 60 000" in text


def test_extended_report_has_executor_section():
    text = compose_extended_report(
        _scan(),
        [_finding(), _finding(id=2, type="seo", penalty_code="seo_title_short", legal_article=None, max_penalty=None)],
    )
    assert "разработчика" in text.lower()
    assert "penalty_code" in text