from app.reports.compose import _report_findings
from types import SimpleNamespace


def test_nuclei_timeout_creates_no_public_finding():
    """Таймаут Nuclei — пустой список (см. nuclei_scan.run_nuclei_scan)."""
    # Регресс: coverage не попадает в сводку отчёта.
    cov = SimpleNamespace(type="coverage", severity="low", id=1)
    facts = SimpleNamespace(type="security", severity="low", id=2)
    assert len(_report_findings([cov, facts])) == 1