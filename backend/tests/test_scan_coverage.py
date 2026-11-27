from types import SimpleNamespace

from app.reports.compose import _scope_section
from app.scan.scan_coverage import nuclei_time_budget_finding


def test_nuclei_timeout_is_coverage_not_security():
    row = nuclei_time_budget_finding("https://example.com/", timeout_sec=120)
    assert row["type"] == "coverage"
    assert row["max_penalty"] is None
    assert row["legal_article"] is None


def test_coverage_note_in_scope_section():
    cov = SimpleNamespace(
        type="coverage",
        title="Активная проверка Nuclei не завершилась вовремя",
        description=nuclei_time_budget_finding(
            "https://x.ru/", timeout_sec=120
        )["description"],
    )
    md = _scope_section({}, [cov])
    assert "Доп. проверка" in md
    assert "Nuclei" in md
    assert "## Технические" not in md